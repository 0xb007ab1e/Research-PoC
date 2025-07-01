package services

import (
	"crypto/sha256"
	"encoding/base64"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"auth-service/internal/config"
	"auth-service/internal/models"
)

type OAuthService struct {
	config           *config.Config
	jwtService       *JWTService
	authCodes        map[string]*models.AuthorizationCode
	refreshTokens    map[string]*models.RefreshToken
	mutex            sync.RWMutex
}

func NewOAuthService(cfg *config.Config, jwtService *JWTService) *OAuthService {
	service := &OAuthService{
		config:        cfg,
		jwtService:    jwtService,
		authCodes:     make(map[string]*models.AuthorizationCode),
		refreshTokens: make(map[string]*models.RefreshToken),
	}

	// Start cleanup goroutine
	go service.cleanupExpiredTokens()

	return service
}

func (o *OAuthService) HandleAuthorizationRequest(req *models.AuthorizationRequest) (*models.AuthorizationCode, *models.ErrorResponse) {
	// Validate response_type
	if req.ResponseType != "code" {
		return nil, &models.ErrorResponse{
			Error:            "unsupported_response_type",
			ErrorDescription: "Only 'code' response type is supported",
			State:            req.State,
		}
	}

	// Validate client_id
	if req.ClientID != o.config.OAuth.ClientID {
		return nil, &models.ErrorResponse{
			Error:            "invalid_client",
			ErrorDescription: "Invalid client_id",
			State:            req.State,
		}
	}

	// Validate redirect_uri
	if !o.isValidRedirectURI(req.RedirectURI) {
		return nil, &models.ErrorResponse{
			Error:            "invalid_request",
			ErrorDescription: "Invalid redirect_uri",
			State:            req.State,
		}
	}

	// Validate PKCE (required in OAuth 2.1)
	if o.config.OAuth.PKCERequired {
		if req.CodeChallenge == "" {
			return nil, &models.ErrorResponse{
				Error:            "invalid_request",
				ErrorDescription: "code_challenge is required",
				State:            req.State,
			}
		}

		if req.CodeChallengeMethod == "" {
			req.CodeChallengeMethod = "plain" // Default per spec
		}

		if req.CodeChallengeMethod != "S256" && req.CodeChallengeMethod != "plain" {
			return nil, &models.ErrorResponse{
				Error:            "invalid_request",
				ErrorDescription: "Invalid code_challenge_method. Only 'S256' and 'plain' are supported",
				State:            req.State,
			}
		}
	}

	// Validate scope
	if !o.isValidScope(req.Scope) {
		return nil, &models.ErrorResponse{
			Error:            "invalid_scope",
			ErrorDescription: "Invalid or unsupported scope",
			State:            req.State,
		}
	}

	// Generate authorization code
	code := uuid.New().String()
	authCode := &models.AuthorizationCode{
		Code:                code,
		ClientID:            req.ClientID,
		RedirectURI:         req.RedirectURI,
		Scope:               req.Scope,
		State:               req.State,
		CodeChallenge:       req.CodeChallenge,
		CodeChallengeMethod: req.CodeChallengeMethod,
		Nonce:               req.Nonce,
		ExpiresAt:           time.Now().Add(o.config.OAuth.CodeExpiration),
		UserID:              "demo-user", // In a real implementation, this would come from authentication
	}

	o.mutex.Lock()
	o.authCodes[code] = authCode
	o.mutex.Unlock()

	return authCode, nil
}

func (o *OAuthService) HandleTokenRequest(req *models.TokenRequest) (*models.TokenResponse, *models.ErrorResponse) {
	switch req.GrantType {
	case "authorization_code":
		return o.handleAuthorizationCodeGrant(req)
	case "refresh_token":
		return o.handleRefreshTokenGrant(req)
	default:
		return nil, &models.ErrorResponse{
			Error:            "unsupported_grant_type",
			ErrorDescription: "Only 'authorization_code' and 'refresh_token' grant types are supported",
		}
	}
}

func (o *OAuthService) handleAuthorizationCodeGrant(req *models.TokenRequest) (*models.TokenResponse, *models.ErrorResponse) {
	// Validate client_id
	if req.ClientID != o.config.OAuth.ClientID {
		return nil, &models.ErrorResponse{
			Error:            "invalid_client",
			ErrorDescription: "Invalid client_id",
		}
	}

	// Get and validate authorization code
	o.mutex.RLock()
	authCode, exists := o.authCodes[req.Code]
	o.mutex.RUnlock()

	if !exists {
		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Invalid authorization code",
		}
	}

	// Check if code is expired
	if time.Now().After(authCode.ExpiresAt) {
		// Remove expired code
		o.mutex.Lock()
		delete(o.authCodes, req.Code)
		o.mutex.Unlock()

		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Authorization code expired",
		}
	}

	// Validate client_id matches
	if authCode.ClientID != req.ClientID {
		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Client ID mismatch",
		}
	}

	// Validate redirect_uri matches
	if authCode.RedirectURI != req.RedirectURI {
		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Redirect URI mismatch",
		}
	}

	// Validate PKCE
	if o.config.OAuth.PKCERequired && authCode.CodeChallenge != "" {
		if req.CodeVerifier == "" {
			return nil, &models.ErrorResponse{
				Error:            "invalid_request",
				ErrorDescription: "code_verifier is required",
			}
		}

		if !o.verifyPKCE(authCode.CodeChallenge, authCode.CodeChallengeMethod, req.CodeVerifier) {
			return nil, &models.ErrorResponse{
				Error:            "invalid_grant",
				ErrorDescription: "Invalid code_verifier",
			}
		}
	}

	// Remove the used authorization code
	o.mutex.Lock()
	delete(o.authCodes, req.Code)
	o.mutex.Unlock()

	// Generate access token with tenant_id
	if o.jwtService == nil {
		return nil, &models.ErrorResponse{
			Error:            "server_error",
			ErrorDescription: "JWT service not configured",
		}
	}
	
	// For demo purposes, derive tenant_id from user_id or use a default
	// In production, this would come from user authentication context
	tenantID := "tenant-" + authCode.UserID // Simple demo mapping
	
	accessToken, err := o.jwtService.GenerateAccessTokenWithTenant(authCode.UserID, authCode.ClientID, authCode.Scope, tenantID)
	if err != nil {
		return nil, &models.ErrorResponse{
			Error:            "server_error",
			ErrorDescription: "Failed to generate access token",
		}
	}

	// Generate refresh token
	refreshToken := uuid.New().String()
	refreshTokenData := &models.RefreshToken{
		Token:     refreshToken,
		ClientID:  authCode.ClientID,
		UserID:    authCode.UserID,
		Scope:     authCode.Scope,
		ExpiresAt: time.Now().Add(o.config.JWT.RefreshTokenTTL),
	}

	o.mutex.Lock()
	o.refreshTokens[refreshToken] = refreshTokenData
	o.mutex.Unlock()

	response := &models.TokenResponse{
		AccessToken:  accessToken,
		TokenType:    "Bearer",
		ExpiresIn:    int64(o.config.JWT.TokenExpiration.Seconds()),
		RefreshToken: refreshToken,
		Scope:        authCode.Scope,
	}

	// Generate ID token if openid scope is requested
	if strings.Contains(authCode.Scope, "openid") {
		idToken, err := o.jwtService.GenerateIDToken(authCode.UserID, authCode.ClientID, authCode.Nonce)
		if err == nil {
			response.IDToken = idToken
		}
	}

	return response, nil
}

func (o *OAuthService) handleRefreshTokenGrant(req *models.TokenRequest) (*models.TokenResponse, *models.ErrorResponse) {
	// Validate client_id
	if req.ClientID != o.config.OAuth.ClientID {
		return nil, &models.ErrorResponse{
			Error:            "invalid_client",
			ErrorDescription: "Invalid client_id",
		}
	}

	// Get and validate refresh token
	o.mutex.RLock()
	refreshTokenData, exists := o.refreshTokens[req.RefreshToken]
	o.mutex.RUnlock()

	if !exists {
		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Invalid refresh token",
		}
	}

	// Check if refresh token is expired
	if time.Now().After(refreshTokenData.ExpiresAt) {
		// Remove expired refresh token
		o.mutex.Lock()
		delete(o.refreshTokens, req.RefreshToken)
		o.mutex.Unlock()

		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Refresh token expired",
		}
	}

	// Validate client_id matches
	if refreshTokenData.ClientID != req.ClientID {
		return nil, &models.ErrorResponse{
			Error:            "invalid_grant",
			ErrorDescription: "Client ID mismatch",
		}
	}

	// Generate new access token
	if o.jwtService == nil {
		return nil, &models.ErrorResponse{
			Error:            "server_error",
			ErrorDescription: "JWT service not configured",
		}
	}
	
	accessToken, err := o.jwtService.GenerateAccessToken(refreshTokenData.UserID, refreshTokenData.ClientID, refreshTokenData.Scope)
	if err != nil {
		return nil, &models.ErrorResponse{
			Error:            "server_error",
			ErrorDescription: "Failed to generate access token",
		}
	}

	response := &models.TokenResponse{
		AccessToken: accessToken,
		TokenType:   "Bearer",
		ExpiresIn:   int64(o.config.JWT.TokenExpiration.Seconds()),
		Scope:       refreshTokenData.Scope,
	}

	return response, nil
}

func (o *OAuthService) IntrospectToken(token string) (*models.IntrospectionResponse, error) {
	if o.jwtService == nil {
		return &models.IntrospectionResponse{
			Active: false,
		}, nil
	}
	
	claims, err := o.jwtService.ValidateAccessToken(token)
	if err != nil {
		// Token is invalid or expired
		return &models.IntrospectionResponse{
			Active: false,
		}, nil
	}

	return &models.IntrospectionResponse{
		Active:    true,
		ClientID:  claims.ClientID,
		Username:  claims.Subject, // Using subject as username
		Scope:     claims.Scope,
		TokenType: "Bearer",
		Exp:       claims.ExpiresAt,
		Iat:       claims.IssuedAt,
		Nbf:       claims.NotBefore,
		Sub:       claims.Subject,
		Aud:       strings.Join(claims.Audience, " "),
		Iss:       claims.Issuer,
		Jti:       claims.JWTID,
	}, nil
}

func (o *OAuthService) isValidRedirectURI(uri string) bool {
	for _, validURI := range o.config.OAuth.RedirectURIs {
		if uri == validURI {
			return true
		}
	}
	return false
}

func (o *OAuthService) isValidScope(scope string) bool {
	if scope == "" {
		return true // Empty scope is valid
	}

	requestedScopes := strings.Split(scope, " ")
	for _, requested := range requestedScopes {
		found := false
		for _, supported := range o.config.OAuth.SupportedScopes {
			if requested == supported {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

func (o *OAuthService) verifyPKCE(codeChallenge, method, codeVerifier string) bool {
	switch method {
	case "plain":
		return codeChallenge == codeVerifier
	case "S256":
		hash := sha256.Sum256([]byte(codeVerifier))
		challenge := base64.RawURLEncoding.EncodeToString(hash[:])
		return codeChallenge == challenge
	default:
		return false
	}
}

func (o *OAuthService) cleanupExpiredTokens() {
	ticker := time.NewTicker(time.Hour)
	defer ticker.Stop()

	for range ticker.C {
		now := time.Now()

		o.mutex.Lock()
		// Clean expired authorization codes
		for code, authCode := range o.authCodes {
			if now.After(authCode.ExpiresAt) {
				delete(o.authCodes, code)
			}
		}

		// Clean expired refresh tokens
		for token, refreshToken := range o.refreshTokens {
			if now.After(refreshToken.ExpiresAt) {
				delete(o.refreshTokens, token)
			}
		}
		o.mutex.Unlock()
	}
}
