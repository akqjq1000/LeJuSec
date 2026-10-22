// Package client sends signed inventory to the control plane.
package client

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/akqjq1000/LeJuSec/agent/internal/collector"
	"github.com/akqjq1000/LeJuSec/agent/internal/signing"
)

// SendInventory marshals the inventory, signs the exact JSON bytes, and POSTs
// them to the control plane with the signature in the X-Signature header.
func SendInventory(
	serverURL string,
	assetID int,
	priv ed25519.PrivateKey,
	inv collector.Inventory,
) error {
	body, err := json.Marshal(inv)
	if err != nil {
		return err
	}

	url := fmt.Sprintf("%s/assets/%d/inventory", serverURL, assetID)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Signature", signing.Sign(priv, body))

	httpClient := &http.Client{Timeout: 30 * time.Second}
	resp, err := httpClient.Do(req)
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
