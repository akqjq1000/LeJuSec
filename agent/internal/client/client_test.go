package client

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
)

func makeCA(t *testing.T) (*x509.Certificate, ed25519.PrivateKey) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{CommonName: "test-ca"},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().Add(time.Hour),
		IsCA:                  true,
		KeyUsage:              x509.KeyUsageCertSign,
		BasicConstraintsValid: true,
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, pub, priv)
	if err != nil {
		t.Fatal(err)
	}
	cert, err := x509.ParseCertificate(der)
	if err != nil {
		t.Fatal(err)
	}
	return cert, priv
}

func makeLeaf(
	t *testing.T, ca *x509.Certificate, caKey ed25519.PrivateKey, cn string, eku x509.ExtKeyUsage,
) (certPEM, keyPEM []byte) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(2),
		Subject:      pkix.Name{CommonName: cn},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{eku},
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, ca, pub, caKey)
	if err != nil {
		t.Fatal(err)
	}
	keyDER, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		t.Fatal(err)
	}
	certPEM = pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
	keyPEM = pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: keyDER})
	return certPEM, keyPEM
}

func writeFile(t *testing.T, path string, data []byte) {
	t.Helper()
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestSendInventoryMTLS(t *testing.T) {
	ca, caKey := makeCA(t)
	clientCertPEM, clientKeyPEM := makeLeaf(t, ca, caKey, "lejusec-agent", x509.ExtKeyUsageClientAuth)

	dir := t.TempDir()
	clientCertPath := filepath.Join(dir, "client.crt")
	clientKeyPath := filepath.Join(dir, "client.key")
	writeFile(t, clientCertPath, clientCertPEM)
	writeFile(t, clientKeyPath, clientKeyPEM)

	clientCAs := x509.NewCertPool()
	clientCAs.AddCert(ca)

	srv := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusCreated)
	}))
	srv.TLS = &tls.Config{
		ClientAuth: tls.RequireAndVerifyClientCert,
		ClientCAs:  clientCAs,
		MinVersion: tls.VersionTLS12,
	}
	srv.StartTLS()
	defer srv.Close()

	serverCAPath := filepath.Join(dir, "serverca.crt")
	writeFile(t, serverCAPath, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE", Bytes: srv.Certificate().Raw},
	))

	tlsConf, err := BuildTLSConfig(TLSPaths{
		ClientCert: clientCertPath,
		ClientKey:  clientKeyPath,
		CACert:     serverCAPath,
	})
	if err != nil {
		t.Fatal(err)
	}

	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	inv := collector.Inventory{Packages: []collector.Package{}, Processes: []collector.Process{}}

	if err := New(srv.URL, tlsConf).SendInventory(1, priv, inv); err != nil {
		t.Fatalf("mTLS send failed: %v", err)
	}

	// 클라이언트 인증서 없이는 서버가 핸드셰이크를 거부해야 한다.
	noCert := &tls.Config{RootCAs: tlsConf.RootCAs, MinVersion: tls.VersionTLS12}
	if err := New(srv.URL, noCert).SendInventory(1, priv, inv); err == nil {
		t.Fatal("expected failure without client certificate")
	}
}
