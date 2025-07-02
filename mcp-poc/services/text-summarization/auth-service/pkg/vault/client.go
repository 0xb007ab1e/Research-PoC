package vault

import (
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
	"math/big"
	"sync"
	"time"

	"github.com/go-jose/go-jose/v4"
	"github.com/hashicorp/vault/api"
)

type Client struct {
	vault      *api.Client
	transitKey string
	keyCache   *keyCache
	mutex      sync.RWMutex
}

type keyCache struct {
	publicKey *rsa.PublicKey
	keyID     string
	expiresAt time.Time
}

type VaultSignResponse struct {
	Data struct {
		Signature string `json:"signature"`
	} `json:"data"`
}

type VaultPublicKeyResponse struct {
	Data struct {
		Keys map[string]interface{} `json:"keys"`
	} `json:"data"`
}

func NewClient(vaultAddr, vaultToken, transitKey string) (*Client, error) {
	config := api.DefaultConfig()
	config.Address = vaultAddr

	vaultClient, err := api.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create vault client: %w", err)
	}

	vaultClient.SetToken(vaultToken)

	client := &Client{
		vault:      vaultClient,
		transitKey: transitKey,
	}

	// Initialize the key on startup
	if err := client.ensureKey(); err != nil {
		return nil, fmt.Errorf("failed to ensure transit key: %w", err)
	}

	return client, nil
}

func (c *Client) ensureKey() error {
	// Check if key exists, create if not
	_, err := c.vault.Logical().Read(fmt.Sprintf("transit/keys/%s", c.transitKey))
	if err != nil {
		// Key doesn't exist, create it
		data := map[string]interface{}{
			"type":                "rsa-2048",
			"exportable":          false,
			"allow_plaintext_backup": false,
		}

		_, err = c.vault.Logical().Write(fmt.Sprintf("transit/keys/%s", c.transitKey), data)
		if err != nil {
			return fmt.Errorf("failed to create transit key: %w", err)
		}
	}

	return nil
}

func (c *Client) SignJWT(payload []byte) (string, error) {
	c.mutex.RLock()
	defer c.mutex.RUnlock()

	// Base64url encode the payload
	encodedPayload := base64.RawURLEncoding.EncodeToString(payload)

	data := map[string]interface{}{
		"input":           encodedPayload,
		"signature_algorithm": "pss",
		"marshaling_algorithm": "jws",
	}

	path := fmt.Sprintf("transit/sign/%s", c.transitKey)
	resp, err := c.vault.Logical().Write(path, data)
	if err != nil {
		return "", fmt.Errorf("failed to sign JWT: %w", err)
	}

	signature, ok := resp.Data["signature"].(string)
	if !ok {
		return "", fmt.Errorf("invalid signature response from vault")
	}

	return signature, nil
}

func (c *Client) GetPublicKey() (*rsa.PublicKey, string, error) {
	c.mutex.RLock()
	if c.keyCache != nil && time.Now().Before(c.keyCache.expiresAt) {
		defer c.mutex.RUnlock()
		return c.keyCache.publicKey, c.keyCache.keyID, nil
	}
	c.mutex.RUnlock()

	c.mutex.Lock()
	defer c.mutex.Unlock()

	// Double-check after acquiring write lock
	if c.keyCache != nil && time.Now().Before(c.keyCache.expiresAt) {
		return c.keyCache.publicKey, c.keyCache.keyID, nil
	}

	path := fmt.Sprintf("transit/keys/%s", c.transitKey)
	resp, err := c.vault.Logical().Read(path)
	if err != nil {
		return nil, "", fmt.Errorf("failed to read public key: %w", err)
	}

	keys, ok := resp.Data["keys"].(map[string]interface{})
	if !ok {
		return nil, "", fmt.Errorf("invalid keys response from vault")
	}

	// Get the latest key version
	var latestVersion int
	var latestKey map[string]interface{}
	for version, keyData := range keys {
		if keyMap, ok := keyData.(map[string]interface{}); ok {
			if v := version; v > fmt.Sprintf("%d", latestVersion) {
				latestVersion++
				latestKey = keyMap
			}
		}
	}

	if latestKey == nil {
		return nil, "", fmt.Errorf("no valid key found")
	}

	publicKeyPEM, ok := latestKey["public_key"].(string)
	if !ok {
		return nil, "", fmt.Errorf("invalid public key format")
	}

	// Parse PEM
	block, _ := pem.Decode([]byte(publicKeyPEM))
	if block == nil {
		return nil, "", fmt.Errorf("failed to decode PEM block")
	}

	publicKey, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, "", fmt.Errorf("failed to parse public key: %w", err)
	}

	rsaPublicKey, ok := publicKey.(*rsa.PublicKey)
	if !ok {
		return nil, "", fmt.Errorf("public key is not RSA")
	}

	keyID := fmt.Sprintf("%s-v%d", c.transitKey, latestVersion)

	// Cache the key for 23 hours (rotate every 24 hours)
	c.keyCache = &keyCache{
		publicKey: rsaPublicKey,
		keyID:     keyID,
		expiresAt: time.Now().Add(23 * time.Hour),
	}

	return rsaPublicKey, keyID, nil
}

func (c *Client) GetJWKS() (*jose.JSONWebKeySet, error) {
	publicKey, keyID, err := c.GetPublicKey()
	if err != nil {
		return nil, err
	}

	jwk := jose.JSONWebKey{
		Key:       publicKey,
		KeyID:     keyID,
		Algorithm: "RS256",
		Use:       "sig",
	}

	return &jose.JSONWebKeySet{
		Keys: []jose.JSONWebKey{jwk},
	}, nil
}

func (c *Client) RotateKey() error {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	path := fmt.Sprintf("transit/keys/%s/rotate", c.transitKey)
	_, err := c.vault.Logical().Write(path, nil)
	if err != nil {
		return fmt.Errorf("failed to rotate key: %w", err)
	}

	// Clear cache to force refresh
	c.keyCache = nil

	return nil
}

func (c *Client) VerifyJWT(token string) (bool, error) {
	data := map[string]interface{}{
		"input": token,
	}

	path := fmt.Sprintf("transit/verify/%s", c.transitKey)
	resp, err := c.vault.Logical().Write(path, data)
	if err != nil {
		return false, fmt.Errorf("failed to verify JWT: %w", err)
	}

	valid, ok := resp.Data["valid"].(bool)
	if !ok {
		return false, fmt.Errorf("invalid verification response from vault")
	}

	return valid, nil
}

// Helper function to convert RSA public key to JWK format for JWKS endpoint
func RSAPublicKeyToJWK(publicKey *rsa.PublicKey, keyID string) map[string]interface{} {
	return map[string]interface{}{
		"kty": "RSA",
		"use": "sig",
		"alg": "RS256",
		"kid": keyID,
		"n":   base64.RawURLEncoding.EncodeToString(publicKey.N.Bytes()),
		"e":   base64.RawURLEncoding.EncodeToString(big.NewInt(int64(publicKey.E)).Bytes()),
	}
}
