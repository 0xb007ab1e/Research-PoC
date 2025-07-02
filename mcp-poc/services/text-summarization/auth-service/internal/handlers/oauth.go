package handlers

import (
	"encoding/json"
	"net/http"
	"net/url"

	"auth-service/internal/models"
	"auth-service/internal/services"
	"auth-service/pkg/metrics"
)

type OAuthHandler struct {
	oauthService *services.OAuthService
	jwtService   *services.JWTService
}

func NewOAuthHandler(oauthService *services.OAuthService, jwtService *services.JWTService) *OAuthHandler {
	return &OAuthHandler{
		oauthService: oauthService,
		jwtService:   jwtService,
	}
}

// HandleAuthorize handles the OAuth2.1 authorization endpoint
func (h *OAuthHandler) HandleAuthorize(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse query parameters
	req := &models.AuthorizationRequest{
		ResponseType:        r.URL.Query().Get("response_type"),
		ClientID:            r.URL.Query().Get("client_id"),
		RedirectURI:         r.URL.Query().Get("redirect_uri"),
		Scope:               r.URL.Query().Get("scope"),
		State:               r.URL.Query().Get("state"),
		CodeChallenge:       r.URL.Query().Get("code_challenge"),
		CodeChallengeMethod: r.URL.Query().Get("code_challenge_method"),
		Nonce:               r.URL.Query().Get("nonce"),
	}

	// Validate request
	if req.ResponseType == "" || req.ClientID == "" || req.RedirectURI == "" {
		errorResp := &models.ErrorResponse{
			Error:            "invalid_request",
			ErrorDescription: "Missing required parameters",
			State:            req.State,
		}
		h.sendErrorResponse(w, r, errorResp, req.RedirectURI)
		return
	}

	// Process authorization request
	authCode, errorResp := h.oauthService.HandleAuthorizationRequest(req)
	if errorResp != nil {
		metrics.RecordAuthorizationRequest(req.ClientID, req.ResponseType, "error")
		h.sendErrorResponse(w, r, errorResp, req.RedirectURI)
		return
	}

	metrics.RecordAuthorizationRequest(req.ClientID, req.ResponseType, "success")

	// Redirect back to client with authorization code
	redirectURL, err := url.Parse(req.RedirectURI)
	if err != nil {
		errorResp := &models.ErrorResponse{
			Error:            "invalid_request",
			ErrorDescription: "Invalid redirect_uri",
			State:            req.State,
		}
		h.sendErrorResponse(w, r, errorResp, req.RedirectURI)
		return
	}

	params := redirectURL.Query()
	params.Set("code", authCode.Code)
	if req.State != "" {
		params.Set("state", req.State)
	}
	redirectURL.RawQuery = params.Encode()

	http.Redirect(w, r, redirectURL.String(), http.StatusFound)
}

// HandleToken handles the OAuth2.1 token endpoint
func (h *OAuthHandler) HandleToken(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse form data
	if err := r.ParseForm(); err != nil {
		h.sendTokenErrorResponse(w, &models.ErrorResponse{
			Error:            "invalid_request",
			ErrorDescription: "Failed to parse request",
		})
		return
	}

	req := &models.TokenRequest{
		GrantType:    r.FormValue("grant_type"),
		Code:         r.FormValue("code"),
		RedirectURI:  r.FormValue("redirect_uri"),
		ClientID:     r.FormValue("client_id"),
		CodeVerifier: r.FormValue("code_verifier"),
		RefreshToken: r.FormValue("refresh_token"),
	}

	// Validate required parameters
	if req.GrantType == "" || req.ClientID == "" {
		h.sendTokenErrorResponse(w, &models.ErrorResponse{
			Error:            "invalid_request",
			ErrorDescription: "Missing required parameters",
		})
		return
	}

	// Process token request
	tokenResp, errorResp := h.oauthService.HandleTokenRequest(req)
	if errorResp != nil {
		metrics.RecordTokenRequest(req.ClientID, req.GrantType, "error")
		h.sendTokenErrorResponse(w, errorResp)
		return
	}

	metrics.RecordTokenRequest(req.ClientID, req.GrantType, "success")
	metrics.RecordJWTTokenGenerated("access_token", req.ClientID)
	if tokenResp.IDToken != "" {
		metrics.RecordJWTTokenGenerated("id_token", req.ClientID)
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Pragma", "no-cache")
	json.NewEncoder(w).Encode(tokenResp)
}

// HandleJWKS handles the JWKS endpoint
func (h *OAuthHandler) HandleJWKS(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	jwks, err := h.jwtService.GetJWKS()
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "public, max-age=3600") // Cache for 1 hour
	w.Write(jwks)
}

// HandleIntrospect handles the token introspection endpoint
func (h *OAuthHandler) HandleIntrospect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse form data
	if err := r.ParseForm(); err != nil {
		metrics.RecordIntrospectionRequest("error")
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	token := r.FormValue("token")
	if token == "" {
		metrics.RecordIntrospectionRequest("error")
		http.Error(w, "Missing token parameter", http.StatusBadRequest)
		return
	}

	// Introspect token
	resp, err := h.oauthService.IntrospectToken(token)
	if err != nil {
		metrics.RecordIntrospectionRequest("error")
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	if resp.Active {
		metrics.RecordIntrospectionRequest("success")
		metrics.RecordJWTValidation("valid")
	} else {
		metrics.RecordIntrospectionRequest("inactive")
		metrics.RecordJWTValidation("invalid")
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// HandleHealth handles health check endpoint
func (h *OAuthHandler) HandleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	health := map[string]string{
		"status": "healthy",
		"service": "auth-service",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}

// sendErrorResponse sends an OAuth error response
func (h *OAuthHandler) sendErrorResponse(w http.ResponseWriter, r *http.Request, errorResp *models.ErrorResponse, redirectURI string) {
	// If we have a valid redirect URI, redirect with error
	if redirectURI != "" {
		redirectURL, err := url.Parse(redirectURI)
		if err == nil {
			params := redirectURL.Query()
			params.Set("error", errorResp.Error)
			if errorResp.ErrorDescription != "" {
				params.Set("error_description", errorResp.ErrorDescription)
			}
			if errorResp.State != "" {
				params.Set("state", errorResp.State)
			}
			redirectURL.RawQuery = params.Encode()

			http.Redirect(w, r, redirectURL.String(), http.StatusFound)
			return
		}
	}

	// Otherwise, return JSON error response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusBadRequest)
	json.NewEncoder(w).Encode(errorResp)
}

// sendTokenErrorResponse sends a token error response
func (h *OAuthHandler) sendTokenErrorResponse(w http.ResponseWriter, errorResp *models.ErrorResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Pragma", "no-cache")
	w.WriteHeader(http.StatusBadRequest)
	json.NewEncoder(w).Encode(errorResp)
}
