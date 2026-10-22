package signing

import (
	"crypto/ed25519"
	"encoding/base64"
	"os"
	"path/filepath"
	"testing"
)

func TestGenerateLoadSignVerify(t *testing.T) {
	privB64, pubB64, err := GenerateKey()
	if err != nil {
		t.Fatal(err)
	}

	keyPath := filepath.Join(t.TempDir(), "agent.key")
	if err := os.WriteFile(keyPath, []byte(privB64+"\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	priv, err := LoadPrivateKey(keyPath)
	if err != nil {
		t.Fatal(err)
	}
	if PublicB64(priv) != pubB64 {
		t.Fatalf("PublicB64 mismatch: %q != %q", PublicB64(priv), pubB64)
	}

	msg := []byte(`{"packages":[],"processes":[]}`)
	sig, err := base64.StdEncoding.DecodeString(Sign(priv, msg))
	if err != nil {
		t.Fatal(err)
	}
	pub, _ := base64.StdEncoding.DecodeString(pubB64)
	if !ed25519.Verify(ed25519.PublicKey(pub), msg, sig) {
		t.Fatal("valid signature failed to verify")
	}

	tampered := []byte(`{"packages":[],"processes":[1]}`)
	if ed25519.Verify(ed25519.PublicKey(pub), tampered, sig) {
		t.Fatal("tampered message unexpectedly verified")
	}
}

func TestLoadPrivateKeyInvalid(t *testing.T) {
	keyPath := filepath.Join(t.TempDir(), "bad.key")
	if err := os.WriteFile(keyPath, []byte("not-base64!!!"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadPrivateKey(keyPath); err == nil {
		t.Fatal("expected error for invalid key")
	}
}
