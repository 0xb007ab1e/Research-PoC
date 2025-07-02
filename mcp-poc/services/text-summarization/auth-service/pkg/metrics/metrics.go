package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// HTTP request metrics
	HttpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_http_requests_total",
			Help: "Total number of HTTP requests processed",
		},
		[]string{"method", "endpoint", "status_code"},
	)

	HttpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "auth_service_http_request_duration_seconds",
			Help:    "HTTP request duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "endpoint"},
	)

	// OAuth specific metrics
	AuthorizationRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_authorization_requests_total",
			Help: "Total number of OAuth authorization requests",
		},
		[]string{"client_id", "response_type", "status"},
	)

	TokenRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_token_requests_total",
			Help: "Total number of OAuth token requests",
		},
		[]string{"client_id", "grant_type", "status"},
	)

	IntrospectionRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_introspection_requests_total",
			Help: "Total number of token introspection requests",
		},
		[]string{"status"},
	)

	// JWT metrics
	JwtTokensGenerated = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_jwt_tokens_generated_total",
			Help: "Total number of JWT tokens generated",
		},
		[]string{"token_type", "client_id"},
	)

	JwtTokenValidations = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_jwt_token_validations_total",
			Help: "Total number of JWT token validations",
		},
		[]string{"status"},
	)

	// Vault metrics
	VaultOperations = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_service_vault_operations_total",
			Help: "Total number of Vault operations",
		},
		[]string{"operation", "status"},
	)

	VaultOperationDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "auth_service_vault_operation_duration_seconds",
			Help:    "Vault operation duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"operation"},
	)

	// Cache metrics
	KeyCacheHits = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "auth_service_key_cache_hits_total",
			Help: "Total number of key cache hits",
		},
	)

	KeyCacheMisses = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "auth_service_key_cache_misses_total",
			Help: "Total number of key cache misses",
		},
	)

	// Active tokens/codes
	ActiveAuthorizationCodes = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "auth_service_active_authorization_codes",
			Help: "Number of active authorization codes",
		},
	)

	ActiveRefreshTokens = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "auth_service_active_refresh_tokens",
			Help: "Number of active refresh tokens",
		},
	)

	// Key rotation metrics
	KeyRotations = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "auth_service_key_rotations_total",
			Help: "Total number of key rotations",
		},
	)

	KeyRotationDuration = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "auth_service_key_rotation_duration_seconds",
			Help:    "Key rotation duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
	)
)

// Helper functions for common metric operations
func RecordHTTPRequest(method, endpoint, statusCode string) {
	HttpRequestsTotal.WithLabelValues(method, endpoint, statusCode).Inc()
}

func RecordAuthorizationRequest(clientID, responseType, status string) {
	AuthorizationRequestsTotal.WithLabelValues(clientID, responseType, status).Inc()
}

func RecordTokenRequest(clientID, grantType, status string) {
	TokenRequestsTotal.WithLabelValues(clientID, grantType, status).Inc()
}

func RecordIntrospectionRequest(status string) {
	IntrospectionRequestsTotal.WithLabelValues(status).Inc()
}

func RecordJWTTokenGenerated(tokenType, clientID string) {
	JwtTokensGenerated.WithLabelValues(tokenType, clientID).Inc()
}

func RecordJWTValidation(status string) {
	JwtTokenValidations.WithLabelValues(status).Inc()
}

func RecordVaultOperation(operation, status string) {
	VaultOperations.WithLabelValues(operation, status).Inc()
}

func RecordKeyCacheHit() {
	KeyCacheHits.Inc()
}

func RecordKeyCacheMiss() {
	KeyCacheMisses.Inc()
}

func SetActiveAuthorizationCodes(count int) {
	ActiveAuthorizationCodes.Set(float64(count))
}

func SetActiveRefreshTokens(count int) {
	ActiveRefreshTokens.Set(float64(count))
}

func RecordKeyRotation() {
	KeyRotations.Inc()
}
