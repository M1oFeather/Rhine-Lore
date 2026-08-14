package com.rhinelore.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Built-in DeepSeek login helper.
 *
 * Opens platform.deepseek.com in a WebView. After the user logs in and copies
 * an API key (sk-...), an injected script intercepts the copy event and the
 * key is automatically saved to the embedded Rhine-Lore server config.
 */
public class KeyAssistantActivity extends Activity {
    private static final String TAG = "RhineLore";
    private static final int LORE_PORT = 8796;
    private final AtomicBoolean captured = new AtomicBoolean(false);

    private static final String CAPTURE_SCRIPT =
            "(function(){"
            + "var bridge = window.AndroidKeyBridge;"
            + "if(!bridge){return;}"
            + "function capture(text){"
            + "  if(text && typeof text === 'string'){"
            + "    var m = text.trim().match(/sk-[A-Za-z0-9_-]{16,}/);"
            + "    if(m){ bridge.onKeyCaptured(m[0]); }"
            + "  }"
            + "}"
            + "try{"
            + "  if(navigator.clipboard && navigator.clipboard.writeText){"
            + "    var orig = navigator.clipboard.writeText.bind(navigator.clipboard);"
            + "    navigator.clipboard.writeText = function(text){capture(text); return orig(text);};"
            + "  }"
            + "}catch(e){}"
            + "try{"
            + "  var origExec = document.execCommand.bind(document);"
            + "  document.execCommand = function(cmd){"
            + "    if(String(cmd).toLowerCase() === 'copy'){"
            + "      var sel = window.getSelection();"
            + "      if(sel){capture(sel.toString());}"
            + "    }"
            + "    return origExec(cmd);"
            + "  };"
            + "}catch(e){}"
            + "var timer = setInterval(function(){"
            + "  try{"
            + "    var text = document.body ? document.body.innerText : '';"
            + "    var m = text.match(/sk-[A-Za-z0-9_-]{16,}/g);"
            + "    if(m && m.length){ bridge.onKeyCaptured(m[m.length-1]); }"
            + "  }catch(e){}"
            + "}, 3000);"
            + "window.addEventListener('beforeunload', function(){clearInterval(timer);});"
            + "})();";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(CAPTURE_SCRIPT, null);
            }
        });
        webView.addJavascriptInterface(new KeyBridge(), "AndroidKeyBridge");
        setContentView(webView);
        webView.loadUrl("https://platform.deepseek.com/");
    }

    @Override
    public void onBackPressed() {
        WebView webView = (WebView) ((android.widget.FrameLayout) findViewById(android.R.id.content))
                .getChildAt(0);
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    private class KeyBridge {
        @JavascriptInterface
        public void onKeyCaptured(final String key) {
            if (key == null || key.trim().isEmpty() || !captured.compareAndSet(false, true)) {
                return;
            }
            new Thread(() -> saveKey(key.trim())).start();
        }
    }

    private void saveKey(String key) {
        try {
            URL url = new URL("http://127.0.0.1:" + LORE_PORT + "/lore-api/llm/config");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);
            connection.setConnectTimeout(6000);
            connection.setReadTimeout(6000);
            JSONObject body = new JSONObject();
            body.put("base_url", "https://api.deepseek.com");
            body.put("api_key", key);
            body.put("model", "deepseek-v4-flash");
            body.put("preset", "deepseek");
            body.put("level", "balanced");
            OutputStream out = connection.getOutputStream();
            out.write(body.toString().getBytes(StandardCharsets.UTF_8));
            out.close();
            int code = connection.getResponseCode();
            connection.disconnect();
            runOnUiThread(() -> {
                if (code == 200) {
                    Toast.makeText(this, "DeepSeek API Key 已自动配置", Toast.LENGTH_LONG).show();
                    finish();
                } else {
                    Toast.makeText(this, "Key 已获取，但保存失败（HTTP " + code + "）", Toast.LENGTH_LONG).show();
                }
            });
        } catch (Exception error) {
            Log.e(TAG, "save deepseek key failed", error);
            runOnUiThread(() -> Toast.makeText(
                    this,
                    "Key 已获取，但保存失败：" + error.getMessage(),
                    Toast.LENGTH_LONG).show());
        }
    }
}
