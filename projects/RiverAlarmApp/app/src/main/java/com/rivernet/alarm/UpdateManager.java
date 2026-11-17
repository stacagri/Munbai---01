package com.rivernet.alarm;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.widget.Toast;
import androidx.core.app.NotificationCompat;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class UpdateManager {

    public static final String CHANNEL_UPDATE_ID = "rivernet_update_channel";
    public static final int NOTIF_UPDATE_ID = 2002;
    private static volatile boolean isDownloading = false;

    public static void handleUpdatePacket(Context context, int newVersionCode, String newVersionName, String downloadUrl) {
        int currentVersionCode = getCurrentVersionCode(context);
        if (newVersionCode <= currentVersionCode) {
            return; // Already up to date
        }

        if (isDownloading) {
            return; // Download already in progress
        }

        new Handler(Looper.getMainLooper()).post(() -> {
            Toast.makeText(context, "🚀 New Update Found (" + newVersionName + ")! Downloading...", Toast.LENGTH_LONG).show();
        });

        downloadAndInstall(context, newVersionName, downloadUrl);
    }

    public static int getCurrentVersionCode(Context context) {
        try {
            PackageInfo pInfo = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            return pInfo.versionCode;
        } catch (Exception e) {
            return 1;
        }
    }

    private static void downloadAndInstall(Context context, String versionName, String downloadUrl) {
        isDownloading = true;
        createUpdateNotificationChannel(context);

        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        NotificationCompat.Builder notifBuilder = new NotificationCompat.Builder(context, CHANNEL_UPDATE_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("Downloading River Alert " + versionName)
            .setContentText("Downloading update in background...")
            .setOngoing(true)
            .setProgress(0, 0, true)
            .setPriority(NotificationCompat.PRIORITY_HIGH);

        if (nm != null) {
            nm.notify(NOTIF_UPDATE_ID, notifBuilder.build());
        }

        new Thread(() -> {
            File apkFile = null;
            try {
                File dir = context.getExternalCacheDir() != null ? context.getExternalCacheDir() : context.getCacheDir();
                apkFile = new File(dir, "RiverAlert_update.apk");
                if (apkFile.exists()) {
                    apkFile.delete();
                }

                URL url = new URL(downloadUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestProperty("User-Agent", "Mozilla/5.0");
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(30000);
                conn.connect();

                if (conn.getResponseCode() != 200) {
                    throw new Exception("HTTP error code: " + conn.getResponseCode());
                }

                InputStream in = conn.getInputStream();
                FileOutputStream out = new FileOutputStream(apkFile);
                byte[] buffer = new byte[8192];
                int len;
                while ((len = in.read(buffer)) != -1) {
                    out.write(buffer, 0, len);
                }
                out.flush();
                out.close();
                in.close();
                conn.disconnect();

                final File finalApk = apkFile;
                new Handler(Looper.getMainLooper()).post(() -> {
                    if (nm != null) {
                        nm.cancel(NOTIF_UPDATE_ID);
                    }
                    installApk(context, finalApk);
                });

            } catch (Exception e) {
                e.printStackTrace();
                new Handler(Looper.getMainLooper()).post(() -> {
                    if (nm != null) {
                        nm.cancel(NOTIF_UPDATE_ID);
                    }
                    Toast.makeText(context, "❌ Update download failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                });
            } finally {
                isDownloading = false;
            }
        }).start();
    }

    public static void installApk(Context context, File apkFile) {
        if (apkFile == null || !apkFile.exists()) {
            Toast.makeText(context, "Update file not found", Toast.LENGTH_SHORT).show();
            return;
        }

        // On Android 8.0+, check if permission to install unknown apps is granted
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!context.getPackageManager().canRequestPackageInstalls()) {
                Toast.makeText(context, "Please allow 'Install unknown apps' permission to update", Toast.LENGTH_LONG).show();
                Intent permissionIntent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES);
                permissionIntent.setData(Uri.parse("package:" + context.getPackageName()));
                permissionIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(permissionIntent);
                return;
            }
        }

        try {
            Uri apkUri = FileProvider.getUriForFile(
                context,
                context.getPackageName() + ".fileprovider",
                apkFile
            );

            Intent installIntent = new Intent(Intent.ACTION_VIEW);
            installIntent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            installIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(installIntent);
        } catch (Exception e) {
            Toast.makeText(context, "Install error: " + e.getMessage(), Toast.LENGTH_LONG).show();
            e.printStackTrace();
        }
    }

    private static void createUpdateNotificationChannel(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = context.getSystemService(NotificationManager.class);
            if (nm == null) return;

            NotificationChannel channel = new NotificationChannel(
                CHANNEL_UPDATE_ID,
                "App Updates",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Shows download progress and install prompts for River Alert updates");
            nm.createNotificationChannel(channel);
        }
    }
}
