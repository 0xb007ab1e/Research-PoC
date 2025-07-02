package services

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	"auth-service/internal/config"
	"auth-service/internal/models"
	"auth-service/pkg/vault"
)

type JWTService struct {
	vaultClient *vault.Client
	config      *config.Config
}

func NewJWTService(vaultClient *vault.Client, cfg *config.Config) *JWTService {
	return &JWTService{
		vaultClient: vaultClient,
		config:      cfg,
	}
}

func (j *JWTService) GenerateAccessToken(userID, clientID, scope string) (string, error) {
	return j.GenerateAccessTokenWithTenant(userID, clientID, scope, "")
}

func (j *JWTService) GenerateAccessTokenWithTenant(userID, clientID, scope, tenantID string) (string, error) {
	now := time.Now()
	claims := models.Claims{
		Issuer:    j.config.JWT.Issuer,
		Subject:   userID,
		Audience:  []string{j.config.JWT.Audience},
		ExpiresAt: now.Add(j.config.JWT.TokenExpiration).Unix(),
		NotBefore: now.Unix(),
		IssuedAt:  now.Unix(),
		JWTID:     uuid.New().String(),
		Scope:     scope,
		ClientID:  clientID,
		TenantID:  tenantID,
	}

	return j.signJWT(claims)
}

func (j *JWTService) GenerateIDToken(userID, clientID, nonce string) (string, error) {
	now := time.Now()
	claims := models.Claims{
		Issuer:    j.config.JWT.Issuer,
		Subject:   userID,
		Audience:  []string{clientID},
		ExpiresAt: now.Add(j.config.JWT.TokenExpiration).Unix(),
		NotBefore: now.Unix(),
		IssuedAt:  now.Unix(),
		JWTID:     uuid.New().String(),
	}

	// Add nonce if provided (for OIDC)
	if nonce != "" {
		claimsMap := map[string]interface{}{
			"iss":   claims.Issuer,
			"sub":   claims.Subject,
			"aud":   claims.Audience,
			"exp":   claims.ExpiresAt,
			"nbf":   claims.NotBefore,
			"iat":   claims.IssuedAt,
			"jti":   claims.JWTID,
			"nonce": nonce,
		}
		return j.signJWTFromMap(claimsMap)
	}

	return j.signJWT(claims)
}

func (j *JWTService) signJWT(claims models.Claims) (string, error) {
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", fmt.Errorf("failed to marshal claims: %w", err)
	}

	// Get public key for header
	_, keyID, err := j.vaultClient.GetPublicKey()
	if err != nil {
		return "", fmt.Errorf("failed to get public key: %w", err)
	}

	// Create JWT header
	header := map[string]interface{}{
		"alg": "RS256",
		"typ": "JWT",
		"kid": keyID,
	}

	headerJSON, err := json.Marshal(header)
	if err != nil {
		return "", fmt.Errorf("failed to marshal header: %w", err)
	}

	// Create JWT payload (header.claims)
	headerB64 := base64.RawURLEncoding.EncodeToString(headerJSON)
	claimsB64 := base64.RawURLEncoding.EncodeToString(claimsJSON)
	payload := headerB64 + "." + claimsB64

	// Sign with Vault
	signature, err := j.vaultClient.SignJWT([]byte(payload))
	if err != nil {
		return "", fmt.Errorf("failed to sign JWT: %w", err)
	}

	// Vault returns the signature in the format "vault:v1:signature"
	// We need to extract just the signature part
	parts := len("vault:v1:")
	if len(signature) <= parts {
		return "", fmt.Errorf("invalid signature format from vault")
	}
	actualSignature := signature[parts:]

	return payload + "." + actualSignature, nil
}

func (j *JWTService) signJWTFromMap(claims map[string]interface{}) (string, error) {
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", fmt.Errorf("failed to marshal claims: %w", err)
	}

	// Get public key for header
	_, keyID, err := j.vaultClient.GetPublicKey()
	if err != nil {
		return "", fmt.Errorf("failed to get public key: %w", err)
	}

	// Create JWT header
	header := map[string]interface{}{
		"alg": "RS256",
		"typ": "JWT",
		"kid": keyID,
	}

	headerJSON, err := json.Marshal(header)
	if err != nil {
		return "", fmt.Errorf("failed to marshal header: %w", err)
	}

	// Create JWT payload (header.claims)
	headerB64 := base64.RawURLEncoding.EncodeToString(headerJSON)
	claimsB64 := base64.RawURLEncoding.EncodeToString(claimsJSON)
	payload := headerB64 + "." + claimsB64

	// Sign with Vault
	signature, err := j.vaultClient.SignJWT([]byte(payload))
	if err != nil {
		return "", fmt.Errorf("failed to sign JWT: %w", err)
	}

	// Vault returns the signature in the format "vault:v1:signature"
	// We need to extract just the signature part
	parts := len("vault:v1:")
	if len(signature) <= parts {
		return "", fmt.Errorf("invalid signature format from vault")
	}
	actualSignature := signature[parts:]

	return payload + "." + actualSignature, nil
}

func (j *JWTService) ValidateAccessToken(token string) (*models.Claims, error) {
	// Parse the JWT manually to extract claims
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, fmt.Errorf("invalid JWT format")
	}

	// Decode claims
	claimsBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, fmt.Errorf("failed to decode claims: %w", err)
	}

	var claims models.Claims
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return nil, fmt.Errorf("failed to unmarshal claims: %w", err)
	}

	// Verify signature with Vault
	isValid, err := j.vaultClient.VerifyJWT(token)
	if err != nil {
		return nil, fmt.Errorf("failed to verify JWT signature: %w", err)
	}

	if !isValid {
		return nil, fmt.Errorf("invalid JWT signature")
	}

	// Check expiration
	if time.Now().Unix() > claims.ExpiresAt {
		return nil, fmt.Errorf("token expired")
	}

	// Check not before
	if time.Now().Unix() < claims.NotBefore {
		return nil, fmt.Errorf("token not yet valid")
	}

	// Check issuer
	if claims.Issuer != j.config.JWT.Issuer {
		return nil, fmt.Errorf("invalid issuer")
	}

	return &claims, nil
}

func (j *JWTService) GetJWKS() ([]byte, error) {
	jwks, err := j.vaultClient.GetJWKS()
	if err != nil {
		return nil, fmt.Errorf("failed to get JWKS: %w", err)
	}

	jwksJSON, err := json.Marshal(jwks)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal JWKS: %w", err)
	}

	return jwksJSON, nil
}

func (j *JWTService) RotateKeys() error {
	return j.vaultClient.RotateKey()
}
