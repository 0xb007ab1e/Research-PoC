package main

import (
	"database/sql"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"strings"

	_ "github.com/lib/pq"
)

func main() {
	var (
		databaseURL  = flag.String("database-url", os.Getenv("DATABASE_URL"), "PostgreSQL database URL")
		migrationType = flag.String("type", "base", "Migration type: 'base' or 'tenant'")
		tenantSchema = flag.String("tenant-schema", "", "Tenant schema name (required for tenant migrations)")
		sqlFile      = flag.String("sql-file", "", "SQL file to execute")
	)
	flag.Parse()

	if *databaseURL == "" {
		log.Fatal("DATABASE_URL environment variable or -database-url flag is required")
	}

	db, err := sql.Open("postgres", *databaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	// Test connection
	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}

	switch *migrationType {
	case "base":
		if err := runBaseMigrations(db); err != nil {
			log.Fatalf("Failed to run base migrations: %v", err)
		}
		fmt.Println("Base migrations completed successfully")

	case "tenant":
		if *tenantSchema == "" {
			log.Fatal("tenant-schema is required for tenant migrations")
		}
		if err := runTenantMigrations(db, *tenantSchema); err != nil {
			log.Fatalf("Failed to run tenant migrations: %v", err)
		}
		fmt.Printf("Tenant migrations completed successfully for schema: %s\n", *tenantSchema)

	case "custom":
		if *sqlFile == "" {
			log.Fatal("sql-file is required for custom migrations")
		}
		if err := runCustomMigration(db, *sqlFile, *tenantSchema); err != nil {
			log.Fatalf("Failed to run custom migration: %v", err)
		}
		fmt.Printf("Custom migration completed successfully: %s\n", *sqlFile)

	default:
		log.Fatalf("Invalid migration type: %s. Must be 'base', 'tenant', or 'custom'", *migrationType)
	}
}

func runBaseMigrations(db *sql.DB) error {
	sqlFile := "../sql/001_create_base_schema.sql"
	return executeSQLFile(db, sqlFile, "")
}

func runTenantMigrations(db *sql.DB, tenantSchema string) error {
	// First create the schema
	_, err := db.Exec(fmt.Sprintf("CREATE SCHEMA IF NOT EXISTS %s", tenantSchema))
	if err != nil {
		return fmt.Errorf("failed to create schema %s: %v", tenantSchema, err)
	}

	// Run the tenant template migration
	sqlFile := "../sql/002_create_tenant_schema_template.sql"
	return executeSQLFile(db, sqlFile, tenantSchema)
}

func runCustomMigration(db *sql.DB, sqlFile string, tenantSchema string) error {
	return executeSQLFile(db, sqlFile, tenantSchema)
}

func executeSQLFile(db *sql.DB, filename string, tenantSchema string) error {
	// Read SQL file
	content, err := ioutil.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("failed to read SQL file %s: %v", filename, err)
	}

	sqlContent := string(content)

	// Replace tenant schema placeholder if provided
	if tenantSchema != "" {
		sqlContent = strings.ReplaceAll(sqlContent, "{{TENANT_SCHEMA}}", tenantSchema)
	}

	// Split SQL content into individual statements
	statements := strings.Split(sqlContent, ";")

	// Execute each statement
	for i, statement := range statements {
		statement = strings.TrimSpace(statement)
		if statement == "" || strings.HasPrefix(statement, "--") {
			continue
		}

		fmt.Printf("Executing statement %d...\n", i+1)
		_, err := db.Exec(statement)
		if err != nil {
			return fmt.Errorf("failed to execute statement %d: %v\nStatement: %s", i+1, err, statement)
		}
	}

	return nil
}
