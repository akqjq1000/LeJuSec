// Package client sends signed inventory and scan findings to the control
// plane, optionally over mutual TLS.
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
	"github.com/akqjq1000/LeJuSec/agent/internal/fim"
	"github.com/akqjq1000/LeJuSec/agent/internal/remediate"
	"github.com/akqjq1000/LeJuSec/agent/internal/scan"
	"github.com/akqjq1000/LeJuSec/agent/internal/signing"
)

// ApprovedRemediation is an approved, not-yet-applied remediation to run.
type ApprovedRemediation struct {
	ID       int    `json:"id"`
	CheckID  string `json:"check_id"`
	Title    string `json:"title"`
	Script   string `json:"script"`
	Rollback string `json:"rollback"`
}

// Client posts signed payloads to a control-plane base URL.
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

// SendInventory signs and POSTs a host inventory snapshot.
func (c *Client) SendInventory(assetID int, priv ed25519.PrivateKey, inv collector.Inventory) error {
	body, err := json.Marshal(inv)
	if err != nil {
		return err
	}
	return c.postSigned(fmt.Sprintf("/assets/%d/inventory", assetID), priv, body)
}

// SendScan signs and POSTs normalized scanner findings for rule evaluation.
func (c *Client) SendScan(assetID int, priv ed25519.PrivateKey, findings []scan.Finding) error {
	body, err := json.Marshal(map[string][]scan.Finding{"findings": findings})
	if err != nil {
		return err
	}
	return c.postSigned(fmt.Sprintf("/assets/%d/scan", assetID), priv, body)
}

// SendIntegrity signs and POSTs a file-integrity manifest.
func (c *Client) SendIntegrity(assetID int, priv ed25519.PrivateKey, manifest fim.Manifest) error {
	body, err := json.Marshal(manifest)
	if err != nil {
		return err
	}
	return c.postSigned(fmt.Sprintf("/assets/%d/integrity", assetID), priv, body)
}

// PullApproved fetches approved, not-yet-applied remediations (signed, empty body).
func (c *Client) PullApproved(assetID int, priv ed25519.PrivateKey) ([]ApprovedRemediation, error) {
	raw, err := c.postSignedResponse(fmt.Sprintf("/assets/%d/remediations/pull", assetID), priv, []byte{})
	if err != nil {
		return nil, err
	}
	var approved []ApprovedRemediation
	if err := json.Unmarshal(raw, &approved); err != nil {
		return nil, err
	}
	return approved, nil
}

// ReportApply signs and POSTs remediation apply results.
func (c *Client) ReportApply(assetID int, priv ed25519.PrivateKey, results []remediate.Result) error {
	body, err := json.Marshal(map[string][]remediate.Result{"results": results})
	if err != nil {
		return err
	}
	return c.postSigned(fmt.Sprintf("/assets/%d/remediations/report", assetID), priv, body)
}

// postSigned signs the exact body bytes (Ed25519) and POSTs them with the
// signature in the X-Signature header.
func (c *Client) postSigned(path string, priv ed25519.PrivateKey, body []byte) error {
	_, err := c.postSignedResponse(path, priv, body)
	return err
}

// postSignedResponse signs the body bytes, POSTs them, and returns the response body.
func (c *Client) postSignedResponse(
	path string, priv ed25519.PrivateKey, body []byte,
) ([]byte, error) {
	req, err := http.NewRequest(http.MethodPost, c.baseURL+path, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Signature", signing.Sign(priv, body))

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer func() { _ = resp.Body.Close() }()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= http.StatusMultipleChoices {
		return nil, fmt.Errorf("server returned %d: %s", resp.StatusCode, string(respBody))
	}
	return respBody, nil
}
