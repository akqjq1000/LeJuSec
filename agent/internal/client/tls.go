package client

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"os"
)

// TLSPaths holds the file paths for mutual-TLS material.
type TLSPaths struct {
	ClientCert string
	ClientKey  string
	CACert     string
}

// BuildTLSConfig loads the client keypair and CA to build a mutual-TLS client
// config: the client presents ClientCert/ClientKey and verifies the server
// against CACert. All three paths are required.
func BuildTLSConfig(p TLSPaths) (*tls.Config, error) {
	cert, err := tls.LoadX509KeyPair(p.ClientCert, p.ClientKey)
	if err != nil {
		return nil, fmt.Errorf("load client keypair: %w", err)
	}
	caPEM, err := os.ReadFile(p.CACert)
	if err != nil {
		return nil, fmt.Errorf("read CA cert: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caPEM) {
		return nil, fmt.Errorf("no certificates found in CA file %q", p.CACert)
	}
	return &tls.Config{
		Certificates: []tls.Certificate{cert},
		RootCAs:      pool,
		MinVersion:   tls.VersionTLS12,
	}, nil
}
