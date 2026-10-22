// Package client sends signed inventory to the control plane, optionally over
// mutual TLS.
package client

import (
	"bytes"
	"crypto/ed25519"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
	"github.com/akqjq1000/LeJuSec/agent/internal/signing"
)

// Client posts inventory to a control-plane base URL.
type Client struct {
	baseURL string
	http    *http.Client
}

// New builds a client. When tlsConf is non-nil the HTTP transport uses it
// (mutual TLS); otherwise plain HTTP is used.
func New(baseURL string, tlsConf *tls.Config) *Client {
	transport := &http.Transport{}
	if tlsConf != nil {
		transport.TLSClientConfig = tlsConf
	}
	return &Client{
		baseURL: baseURL,
		http:    &http.Client{Timeout: 30 * time.Second, Transport: transport},
	}
}

// SendInventory marshals the inventory, signs the exact JSON bytes, and POSTs
// them with the signature in the X-Signature header.
func (c *Client) SendInventory(assetID int, priv ed25519.PrivateKey, inv collector.Inventory) error {
	body, err := json.Marshal(inv)
	if err != nil {
		return err
	}

	url := fmt.Sprintf("%s/assets/%d/inventory", c.baseURL, assetID)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Signature", signing.Sign(priv, body))

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("server returned %d: %s", resp.StatusCode, string(respBody))
	}
	return nil
}
