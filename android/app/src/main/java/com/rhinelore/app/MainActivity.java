package com.rhinelore.app;

import android.app.Activity;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.chaquo.python.Python;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private static final String TAG = "RhineLore";
    private static final int PORT = 8796;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        File uiDir = new File(getFilesDir(), "ui");
        File dataDir = new File(getFilesDir(), "data");
        try {
            copyAssets("ui", uiDir);
        } catch (IOException e) {
            Log.e(TAG, "copy web assets failed", e);
        }

        Python py = Python.getInstance();
        py.getModule("rhine_lore_launcher").callAttr(
                "start_server", dataDir.getAbsolutePath(), uiDir.getAbsolutePath(), PORT);

        WebView webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient());
        setContentView(webView);

        waitForServer(() -> webView.loadUrl("http://127.0.0.1:" + PORT + "/"));
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
            handler.post(() -> Log.e(TAG, "embedded server did not start in time"));
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
