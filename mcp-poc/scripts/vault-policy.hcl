# Policy for text-summarization service to access database credentials
path "database/creds/readonly" {
  capabilities = ["read"]
}

path "database/creds/readwrite" {
  capabilities = ["read"]
}

# Allow renewal of database credentials
path "sys/leases/renew" {
  capabilities = ["update"]
}

# Allow access to auth/token/lookup-self for token validation
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
