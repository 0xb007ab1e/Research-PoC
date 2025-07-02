package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	Server ServerConfig
	Vault  VaultConfig
	JWT    JWTConfig
	OAuth  OAuthConfig
}

type ServerConfig struct {
	Port         string
	TLSCertFile  string
	TLSKeyFile   string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

type VaultConfig struct {
	Address    string
	Token      string
	TransitKey string
}

type JWTConfig struct {
	Issuer           string
	Audience         string
	TokenExpiration  time.Duration
	RefreshTokenTTL  time.Duration
	KeyRotationInterval time.Duration
}

type OAuthConfig struct {
	ClientID           string
	RedirectURIs       []string
	SupportedScopes    []string
	CodeExpiration     time.Duration
	PKCERequired       bool
}

func Load() *Config {
	return &Config{
		Server: ServerConfig{
			Port:         getEnv("SERVER_PORT", "8443"),
			TLSCertFile:  getEnv("TLS_CERT_FILE", "server.crt"),
			TLSKeyFile:   getEnv("TLS_KEY_FILE", "server.key"),
			ReadTimeout:  getDurationEnv("SERVER_READ_TIMEOUT", 30*time.Second),
			WriteTimeout: getDurationEnv("SERVER_WRITE_TIMEOUT", 30*time.Second),
		},
		Vault: VaultConfig{
			Address:    getEnv("VAULT_ADDR", "http://localhost:8200"),
			Token:      getEnv("VAULT_TOKEN", ""),
			TransitKey: getEnv("VAULT_TRANSIT_KEY", "jwt-signing-key"),
		},
		JWT: JWTConfig{
			Issuer:              getEnv("JWT_ISSUER", "https://auth-service"),
			Audience:            getEnv("JWT_AUDIENCE", "api"),
			TokenExpiration:     getDurationEnv("JWT_TOKEN_EXPIRATION", 24*time.Hour),
			RefreshTokenTTL:     getDurationEnv("JWT_REFRESH_TOKEN_TTL", 7*24*time.Hour),
			KeyRotationInterval: getDurationEnv("JWT_KEY_ROTATION_INTERVAL", 24*time.Hour),
		},
		OAuth: OAuthConfig{
			ClientID:        getEnv("OAUTH_CLIENT_ID", "default-client"),
			RedirectURIs:    []string{getEnv("OAUTH_REDIRECT_URI", "http://localhost:3000/callback")},
			SupportedScopes: []string{"openid", "profile", "email"},
			CodeExpiration:  getDurationEnv("OAUTH_CODE_EXPIRATION", 10*time.Minute),
			PKCERequired:    getBoolEnv("OAUTH_PKCE_REQUIRED", true),
		},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getDurationEnv(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}

func getBoolEnv(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}
