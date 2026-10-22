// Package signing provides Ed25519 key handling and detached signatures for
// the agent. Inventory is signed over the exact JSON bytes that are sent, so
// the control plane can verify without re-canonicalizing.
package signing

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"os"
	"strings"
)

// GenerateKey creates an Ed25519 keypair, returning base64-encoded private
// (64 bytes) and public (32 bytes) keys.
func GenerateKey() (privB64, pubB64 string, err error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return "", "", err
	}
	return base64.StdEncoding.EncodeToString(priv), base64.StdEncoding.EncodeToString(pub), nil
}

// LoadPrivateKey reads a base64-encoded Ed25519 private key from a file.
func LoadPrivateKey(path string) (ed25519.PrivateKey, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(string(data)))
	if err != nil {
		return nil, fmt.Errorf("decode private key: %w", err)
	}
	if len(raw) != ed25519.PrivateKeySize {
		return nil, fmt.Errorf("invalid private key size: got %d, want %d", len(raw), ed25519.PrivateKeySize)
	}
	return ed25519.PrivateKey(raw), nil
}

// Sign returns the base64-encoded Ed25519 signature over message.
func Sign(priv ed25519.PrivateKey, message []byte) string {
	return base64.StdEncoding.EncodeToString(ed25519.Sign(priv, message))
}

// PublicB64 returns the base64-encoded public key for a private key.
func PublicB64(priv ed25519.PrivateKey) string {
	pub, _ := priv.Public().(ed25519.PublicKey)
	return base64.StdEncoding.EncodeToString(pub)
}
