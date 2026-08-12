package com.rhinelore.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.pm.ApplicationInfo;
import android.content.Intent;
import android.content.res.AssetManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.chaquo.python.Python;
import com.chaquo.python.PyException;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.OutputStream;

import org.json.JSONObject;

public class MainActivity extends Activity {
    private static final String TAG = "RhineLore";
    private static final int PORT = 8796;
    private static final int REQUEST_FILE_CHOOSER = 1001;

    private WebView webView;
    private ValueCallback<Uri[]> uploadCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        boolean isDebuggable = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        if (isDebuggable) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        File uiDir = new File(getFilesDir(), "ui");
        File dataDir = new File(getFilesDir(), "data");
        try {
            copyAssets("ui", uiDir);
        } catch (IOException e) {
            Log.e(TAG, "copy web assets failed", e);
            showError("前端资源拷贝失败：" + e.getMessage());
            return;
        }

        try {
            Python py = Python.getInstance();
            py.getModule("rhine_lore_launcher").callAttr(
                    "start_server", dataDir.getAbsolutePath(), uiDir.getAbsolutePath(), PORT);
        } catch (PyException e) {
            Log.e(TAG, "start embedded server failed", e);
            showError("内嵌服务启动失败：" + e.getMessage());
            return;
        }

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showError("页面加载失败：" + error.getDescription());
                }
            }

            @SuppressWarnings("deprecation")
            @Override
            public void onReceivedError(WebView view, int errorCode, String description,
                                        String failingUrl) {
                showError("页面加载失败：" + description);
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> filePathCallback,
                                             FileChooserParams fileChooserParams) {
                if (uploadCallback != null) {
                    uploadCallback.onReceiveValue(null);
                }
                uploadCallback = filePathCallback;
                try {
                    startActivityForResult(fileChooserParams.createIntent(), REQUEST_FILE_CHOOSER);
                } catch (Exception e) {
                    uploadCallback = null;
                    return false;
                }
                return true;
            }
        });
        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void openDeepSeekLogin() {
                startActivity(new Intent(MainActivity.this, KeyAssistantActivity.class));
            }

            @JavascriptInterface
            public String saveBackup(String filename, String base64) {
                try {
                    byte[] data = Base64.decode(base64, Base64.DEFAULT);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        ContentValues values = new ContentValues();
                        values.put(MediaStore.Downloads.DISPLAY_NAME, filename);
                        values.put(MediaStore.Downloads.MIME_TYPE, "application/zip");
                        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                        Uri uri = getContentResolver().insert(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                        if (uri == null) {
                            return "保存失败：无法创建下载条目";
                        }
                        try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                            if (out == null) {
                                return "保存失败：无法打开输出流";
                            }
                            out.write(data);
                        }
                        return "已保存到 下载/" + filename;
                    }
                    File dir = Environment.getExternalStoragePublicDirectory(
                            Environment.DIRECTORY_DOWNLOADS);
                    if (!dir.exists() && !dir.mkdirs()) {
                        return "保存失败：无法创建下载目录";
                    }
                    File file = new File(dir, filename);
                    try (FileOutputStream out = new FileOutputStream(file)) {
                        out.write(data);
                    }
                    return "已保存到 下载/" + filename;
                } catch (Exception e) {
                    Log.e(TAG, "save backup failed", e);
                    return "保存失败：" + e.getMessage();
                }
            }
        }, "AndroidBridge");
        setContentView(webView);

        waitForServer(() -> webView.loadUrl("http://127.0.0.1:" + PORT + "/"));
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_FILE_CHOOSER) {
            if (uploadCallback == null) {
                super.onActivityResult(requestCode, resultCode, data);
                return;
            }
            Uri[] results = null;
            if (resultCode == RESULT_OK && data != null) {
                if (data.getData() != null) {
                    results = new Uri[] {data.getData()};
                } else if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    results = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        results[i] = data.getClipData().getItemAt(i).getUri();
                    }
                }
            }
            uploadCallback.onReceiveValue(results);
            uploadCallback = null;
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    private void showError(String message) {
        if (webView == null) {
            webView = new WebView(this);
            setContentView(webView);
        }
        String html =
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                + "<style>"
                + "body{font-family:sans-serif;background:#1e1e2e;color:#eee;"
                + "display:flex;align-items:center;justify-content:center;"
                + "min-height:100vh;margin:0;padding:24px}"
                + "div{max-width:560px;line-height:1.7}"
                + "h2{color:#ff6b6b;margin-top:0}"
                + "pre{white-space:pre-wrap;word-break:break-all;"
                + "background:#2d2d3f;padding:12px;border-radius:8px}"
                + "</style></head><body><div>"
                + "<h2>Rhine-Lore 启动失败</h2>"
                + "<pre id=\"msg\"></pre>"
                + "<p>请查看 logcat（标签 RhineLore / Python）中的完整错误。</p>"
                + "</div><script>document.getElementById(\"msg\").textContent="
                + JSONObject.quote(message) + ";</script></body></html>";
        webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
    }

    private void waitForServer(Runnable onReady) {
        Handler handler = new Handler(Looper.getMainLooper());
        new Thread(() -> {
            for (int i = 0; i < 60; i++) {
                if (ping()) {
                    handler.post(onReady);
                    return;
                }
                try {
                    Thread.sleep(500);
                } catch (InterruptedException ignored) {
                    return;
                }
            }
            handler.post(() -> {
                Log.e(TAG, "embedded server did not start in time");
                showError("内嵌服务 30 秒内未启动，请确认 logcat 中的 Python 报错。");
            });
        }).start();
    }

    private boolean ping() {
        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(
                    "http://127.0.0.1:" + PORT + "/").openConnection();
            conn.setConnectTimeout(800);
            conn.setReadTimeout(800);
            int code = conn.getResponseCode();
            conn.disconnect();
            return code == 200;
        } catch (IOException e) {
            return false;
        }
    }

    private void copyAssets(String assetPath, File dest) throws IOException {
        AssetManager am = getAssets();
        String[] children = am.list(assetPath);
        if (children == null) {
            return;
        }
        if (children.length == 0) {
            if (dest.getParentFile() != null) {
                dest.getParentFile().mkdirs();
            }
            InputStream in = am.open(assetPath);
            FileOutputStream out = new FileOutputStream(dest);
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) > 0) {
                out.write(buffer, 0, read);
            }
            in.close();
            out.close();
        } else {
            dest.mkdirs();
            for (String child : children) {
                copyAssets(assetPath + "/" + child, new File(dest, child));
            }
        }
    }
}
