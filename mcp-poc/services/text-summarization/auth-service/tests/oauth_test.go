package tests

import (
	"crypto/sha256"
	"encoding/base64"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"auth-service/internal/config"
	"auth-service/internal/models"
	"auth-service/internal/services"
)

func TestOAuthService_HandleAuthorizationRequest(t *testing.T) {
	cfg := &config.Config{
		OAuth: config.OAuthConfig{
			ClientID:        "test-client",
			RedirectURIs:    []string{"http://localhost:3000/callback"},
			SupportedScopes: []string{"openid", "profile", "email"},
			CodeExpiration:  10 * time.Minute,
			PKCERequired:    true,
		},
	}

	oauthService := services.NewOAuthService(cfg, nil)

	t.Run("Valid authorization request with PKCE", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid profile",
			State:               "test-state",
			CodeChallenge:       "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
			CodeChallengeMethod: "S256",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, errorResp)
		assert.NotNil(t, authCode)
		assert.Equal(t, req.ClientID, authCode.ClientID)
		assert.Equal(t, req.RedirectURI, authCode.RedirectURI)
		assert.Equal(t, req.Scope, authCode.Scope)
		assert.Equal(t, req.State, authCode.State)
		assert.Equal(t, req.CodeChallenge, authCode.CodeChallenge)
		assert.Equal(t, req.CodeChallengeMethod, authCode.CodeChallengeMethod)
		assert.NotEmpty(t, authCode.Code)
		assert.True(t, time.Now().Before(authCode.ExpiresAt))
	})

	t.Run("Invalid response type", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType: "token",
			ClientID:     "test-client",
			RedirectURI:  "http://localhost:3000/callback",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, authCode)
		assert.NotNil(t, errorResp)
		assert.Equal(t, "unsupported_response_type", errorResp.Error)
	})

	t.Run("Invalid client ID", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType: "code",
			ClientID:     "invalid-client",
			RedirectURI:  "http://localhost:3000/callback",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, authCode)
		assert.NotNil(t, errorResp)
		assert.Equal(t, "invalid_client", errorResp.Error)
	})

	t.Run("Invalid redirect URI", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType: "code",
			ClientID:     "test-client",
			RedirectURI:  "http://evil.com/callback",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, authCode)
		assert.NotNil(t, errorResp)
		assert.Equal(t, "invalid_request", errorResp.Error)
	})

	t.Run("Missing PKCE when required", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType: "code",
			ClientID:     "test-client",
			RedirectURI:  "http://localhost:3000/callback",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, authCode)
		assert.NotNil(t, errorResp)
		assert.Equal(t, "invalid_request", errorResp.Error)
		assert.Contains(t, errorResp.ErrorDescription, "code_challenge")
	})

	t.Run("Invalid scope", func(t *testing.T) {
		req := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "invalid-scope",
			CodeChallenge:       "test-challenge",
			CodeChallengeMethod: "S256",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(req)

		assert.Nil(t, authCode)
		assert.NotNil(t, errorResp)
		assert.Equal(t, "invalid_scope", errorResp.Error)
	})
}

func TestPKCEVerification(t *testing.T) {
	cfg := &config.Config{
		OAuth: config.OAuthConfig{
			ClientID:        "test-client",
			RedirectURIs:    []string{"http://localhost:3000/callback"},
			SupportedScopes: []string{"openid"},
			CodeExpiration:  10 * time.Minute,
			PKCERequired:    true,
		},
	}

	oauthService := services.NewOAuthService(cfg, nil)

	t.Run("Valid S256 PKCE", func(t *testing.T) {
		codeVerifier := "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
		hash := sha256.Sum256([]byte(codeVerifier))
		codeChallenge := base64.RawURLEncoding.EncodeToString(hash[:])

		// Create authorization request
		authReq := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid",
			CodeChallenge:       codeChallenge,
			CodeChallengeMethod: "S256",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(authReq)
		require.Nil(t, errorResp)
		require.NotNil(t, authCode)

		// Create token request
		tokenReq := &models.TokenRequest{
			GrantType:    "authorization_code",
			Code:         authCode.Code,
			RedirectURI:  authCode.RedirectURI,
			ClientID:     authCode.ClientID,
			CodeVerifier: codeVerifier,
		}

		// This should work with valid PKCE but fail due to nil JWT service
		_, errorResp = oauthService.HandleTokenRequest(tokenReq)
		// We expect server_error because JWT service is nil, but PKCE validation should pass
		if errorResp != nil {
			assert.Equal(t, "server_error", errorResp.Error)
		}
	})

	t.Run("Invalid S256 PKCE", func(t *testing.T) {
		codeVerifier := "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
		hash := sha256.Sum256([]byte(codeVerifier))
		codeChallenge := base64.RawURLEncoding.EncodeToString(hash[:])

		// Create authorization request
		authReq := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid",
			CodeChallenge:       codeChallenge,
			CodeChallengeMethod: "S256",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(authReq)
		require.Nil(t, errorResp)
		require.NotNil(t, authCode)

		// Create token request with wrong verifier
		tokenReq := &models.TokenRequest{
			GrantType:    "authorization_code",
			Code:         authCode.Code,
			RedirectURI:  authCode.RedirectURI,
			ClientID:     authCode.ClientID,
			CodeVerifier: "wrong-verifier",
		}

		_, errorResp = oauthService.HandleTokenRequest(tokenReq)
		assert.Equal(t, "invalid_grant", errorResp.Error)
		assert.Contains(t, errorResp.ErrorDescription, "code_verifier")
	})

	t.Run("Valid plain PKCE", func(t *testing.T) {
		codeVerifier := "test-verifier"

		// Create authorization request
		authReq := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid",
			CodeChallenge:       codeVerifier,
			CodeChallengeMethod: "plain",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(authReq)
		require.Nil(t, errorResp)
		require.NotNil(t, authCode)

		// Create token request
		tokenReq := &models.TokenRequest{
			GrantType:    "authorization_code",
			Code:         authCode.Code,
			RedirectURI:  authCode.RedirectURI,
			ClientID:     authCode.ClientID,
			CodeVerifier: codeVerifier,
		}

		_, errorResp = oauthService.HandleTokenRequest(tokenReq)
		// We expect server_error because JWT service is nil, but PKCE validation should pass
		if errorResp != nil {
			assert.Equal(t, "server_error", errorResp.Error)
		}
	})
}

func TestTokenRequestValidation(t *testing.T) {
	cfg := &config.Config{
		OAuth: config.OAuthConfig{
			ClientID:        "test-client",
			RedirectURIs:    []string{"http://localhost:3000/callback"},
			SupportedScopes: []string{"openid"},
			CodeExpiration:  10 * time.Minute,
			PKCERequired:    true,
		},
	}

	oauthService := services.NewOAuthService(cfg, nil)

	t.Run("Invalid grant type", func(t *testing.T) {
		tokenReq := &models.TokenRequest{
			GrantType: "client_credentials",
			ClientID:  "test-client",
		}

		_, errorResp := oauthService.HandleTokenRequest(tokenReq)
		assert.Equal(t, "unsupported_grant_type", errorResp.Error)
	})

	t.Run("Invalid authorization code", func(t *testing.T) {
		tokenReq := &models.TokenRequest{
			GrantType:   "authorization_code",
			Code:        "invalid-code",
			RedirectURI: "http://localhost:3000/callback",
			ClientID:    "test-client",
		}

		_, errorResp := oauthService.HandleTokenRequest(tokenReq)
		assert.Equal(t, "invalid_grant", errorResp.Error)
	})

	t.Run("Client ID mismatch", func(t *testing.T) {
		// First create a valid authorization code
		authReq := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid",
			CodeChallenge:       "test-challenge",
			CodeChallengeMethod: "plain",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(authReq)
		require.Nil(t, errorResp)
		require.NotNil(t, authCode)

		// Try to use it with different client
		tokenReq := &models.TokenRequest{
			GrantType:    "authorization_code",
			Code:         authCode.Code,
			RedirectURI:  authCode.RedirectURI,
			ClientID:     "different-client",
			CodeVerifier: "test-challenge",
		}

		_, errorResp = oauthService.HandleTokenRequest(tokenReq)
		assert.Equal(t, "invalid_client", errorResp.Error)
		assert.Contains(t, errorResp.ErrorDescription, "Invalid client_id")
	})

	t.Run("Redirect URI mismatch", func(t *testing.T) {
		// First create a valid authorization code
		authReq := &models.AuthorizationRequest{
			ResponseType:        "code",
			ClientID:            "test-client",
			RedirectURI:         "http://localhost:3000/callback",
			Scope:               "openid",
			CodeChallenge:       "test-challenge",
			CodeChallengeMethod: "plain",
		}

		authCode, errorResp := oauthService.HandleAuthorizationRequest(authReq)
		require.Nil(t, errorResp)
		require.NotNil(t, authCode)

		// Try to use it with different redirect URI
		tokenReq := &models.TokenRequest{
			GrantType:    "authorization_code",
			Code:         authCode.Code,
			RedirectURI:  "http://evil.com/callback",
			ClientID:     authCode.ClientID,
			CodeVerifier: "test-challenge",
		}

		_, errorResp = oauthService.HandleTokenRequest(tokenReq)
		assert.Equal(t, "invalid_grant", errorResp.Error)
		assert.Contains(t, errorResp.ErrorDescription, "Redirect URI mismatch")
	})
}
