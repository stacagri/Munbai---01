package com.rivernet.alarm;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import androidx.core.app.NotificationCompat;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class RiverMonitorService extends Service {

    public static final String CHANNEL_MONITOR_ID = "rivernet_silent_monitor_v4";
    public static final String CHANNEL_EMERGENCY_ID = "rivernet_emergency_channel";
    public static final int NOTIF_FOREGROUND_ID = 1001;
    public static final int NOTIF_EMERGENCY_ID = 9999;

    public static final String ACTION_TEST_NOW = "com.rivernet.alarm.ACTION_TEST_NOW";
    public static final String ACTION_TEST_DELAYED = "com.rivernet.alarm.ACTION_TEST_DELAYED";
    public static final String ACTION_STOP_ALARM = "com.rivernet.alarm.ACTION_STOP_ALARM";
    public static final String ACTION_STOP_SERVICE = "com.rivernet.alarm.ACTION_STOP_SERVICE";
    public static final String BROADCAST_STATUS = "com.rivernet.alarm.BROADCAST_STATUS";

    public static final String LIVE_ALERT_TOPIC_URL = "https://ntfy.sh/kalu_ganga_alert_lk_live/raw";

    public static double latestLevel = 0.0;
    public static double alertThreshold = 5.20;
    public static String latestTrend = "Checking...";
    public static String lastCheckTime = "Never";
    public static volatile boolean isRunning = false;
    public static volatile boolean isAlarmActive = false;
    private static long snoozeUntil = 0;

    private Handler handler;
    private Runnable pollRunnable;
    private PowerManager.WakeLock wakeLock;

    private static MediaPlayer activeMediaPlayer;
    private static Vibrator activeVibrator;

    public static void setSnoozeMinutes(int minutes) {
        snoozeUntil = System.currentTimeMillis() + (minutes * 60L * 1000L);
    }

    public static boolean isSnoozed() {
        return System.currentTimeMillis() < snoozeUntil;
    }

    public static synchronized void stopActiveSiren(Context context) {
        isAlarmActive = false;
        if (activeMediaPlayer != null) {
            try {
                if (activeMediaPlayer.isPlaying()) {
                    activeMediaPlayer.stop();
                }
                activeMediaPlayer.release();
            } catch (Exception ignored) {}
            activeMediaPlayer = null;
        }

        if (activeVibrator != null) {
            try {
                activeVibrator.cancel();
            } catch (Exception ignored) {}
            activeVibrator = null;
        }

        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.cancel(NOTIF_EMERGENCY_ID);
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        isRunning = true;
        createNotificationChannels();

        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "RiverAlert::MonitorWakeLock");
            wakeLock.acquire(24 * 60 * 60 * 1000L /* 24 hours */);
        }

        Notification notification = buildForegroundNotification("Watching Kalu Ganga water level & live alerts...");
        startForeground(NOTIF_FOREGROUND_ID, notification);

        // 1. Start live remote push listener
        startRemoteAlertStream();

        // 2. Start periodic RiverNet LK API polling
        handler = new Handler(Looper.getMainLooper());
        pollRunnable = new Runnable() {
            @Override
            public void run() {
                checkRiverLevelAsync();
                handler.postDelayed(this, 3 * 60 * 1000L); // Check every 3 minutes
            }
        };
        handler.post(pollRunnable);
    }

    private void startRemoteAlertStream() {
        new Thread(() -> {
            while (isRunning) {
                HttpURLConnection conn = null;
                try {
                    URL url = new URL(LIVE_ALERT_TOPIC_URL);
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(0); // Stream indefinitely

                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    String line;
                    while (isRunning && (line = reader.readLine()) != null) {
                        line = line.trim();
                        if (!line.isEmpty()) {
                            if (line.startsWith("UPDATE|")) {
                                // Format: UPDATE|versionCode|versionName|downloadUrl
                                String[] parts = line.split("\\|", 4);
                                if (parts.length >= 4) {
                                    try {
                                        int vCode = Integer.parseInt(parts[1].trim());
                                        String vName = parts[2].trim();
                                        String dUrl = parts[3].trim();
                                        UpdateManager.handleUpdatePacket(RiverMonitorService.this, vCode, vName, dUrl);
                                    } catch (Exception ex) {
                                        ex.printStackTrace();
                                    }
                                }
                                continue;
                            }

                            // Only sound siren for genuine emergency broadcasts or test commands
                            if (!line.contains("🚨") && !line.startsWith("ALARM")) {
                                continue;
                            }

                            final String alertMsg = line;
                            new Handler(Looper.getMainLooper()).post(() -> {
                                double lvl = latestLevel > 0 ? latestLevel : 5.48;
                                triggerEmergencyAlert(lvl, alertMsg);
                            });
                        }
                    }
                } catch (Exception e) {
                    try {
                        Thread.sleep(4000);
                    } catch (InterruptedException ignored) {}
                } finally {
                    if (conn != null) {
                        conn.disconnect();
                    }
                }
            }
        }).start();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_TEST_NOW.equals(action)) {
                triggerEmergencyAlert(latestLevel > 0 ? latestLevel : 5.40, "TEST: Flood Siren & Lockscreen Wakeup Test");
            } else if (ACTION_TEST_DELAYED.equals(action)) {
                new Handler(Looper.getMainLooper()).postDelayed(() -> {
                    triggerEmergencyAlert(5.45, "TEST: Lockscreen Emergency Alarm Triggered");
                }, 5000);
            } else if (ACTION_STOP_ALARM.equals(action)) {
                stopActiveSiren(this);
                setSnoozeMinutes(60);
            } else if (ACTION_STOP_SERVICE.equals(action)) {
                stopActiveSiren(this);
                stopForeground(true);
                stopSelf();
                return START_NOT_STICKY;
            }
        }
        return START_STICKY;
    }

    private void checkRiverLevelAsync() {
        new Thread(() -> {
            try {
                String apiUrl = "https://api.rivernet.lk/api/overview/latest-status-paginated?deviceType=river_level&page=1&isTableView=1";
                URL url = new URL(apiUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(15000);

                if (conn.getResponseCode() == 200) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder response = new StringBuilder();
                    String line;
                    while ((line = in.readLine()) != null) {
                        response.append(line);
                    }
                    in.close();

                    parseAndProcessData(response.toString());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private void parseAndProcessData(String jsonString) {
        try {
            JSONObject root = new JSONObject(jsonString);
            JSONArray data = root.optJSONObject("results").optJSONArray("data");
            if (data == null) return;

            for (int i = 0; i < data.length(); i++) {
                JSONObject item = data.getJSONObject(i);
                String unitId = item.optString("unitId", "");
                String location = item.optString("location", "");

                if ("I97".equals(unitId) || location.contains("Ratnapura")) {
                    JSONObject latest = item.optJSONObject("latest");
                    if (latest == null) continue;

                    double level = 0.0;
                    if (latest.has("actualLatestRecord") && !latest.isNull("actualLatestRecord")) {
                        level = latest.getJSONObject("actualLatestRecord").optDouble("value", 0.0);
                    } else if (latest.has("latestLevel")) {
                        level = latest.optDouble("latestLevel", 0.0);
                    }

                    latestLevel = level;
                    int change = latest.optInt("change", 0);
                    String trendText = "Steady (Stable)";
                    if (change == 1) trendText = "RISING ⬆️ (Going Up)";
                    else if (change == -1) trendText = "FALLING ⬇️ (Going Down)";

                    latestTrend = trendText;
                    SimpleDateFormat sdf = new SimpleDateFormat("hh:mm:ss a", Locale.getDefault());
                    lastCheckTime = sdf.format(new Date());

                    Intent broadcastIntent = new Intent(BROADCAST_STATUS);
                    sendBroadcast(broadcastIntent);

                    NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
                    if (nm != null) {
                        String summary = String.format(Locale.US, "Current Level: %.2f m | %s", latestLevel, latestTrend);
                        nm.notify(NOTIF_FOREGROUND_ID, buildForegroundNotification(summary));
                    }
                    break;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public synchronized void triggerEmergencyAlert(double level, String reason) {
        isAlarmActive = true;

        // 1. Force Screen ON via PowerManager
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (pm != null) {
            PowerManager.WakeLock screenLock = pm.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP | PowerManager.ON_AFTER_RELEASE,
                "RiverAlert::EmergencyWakeLock"
            );
            screenLock.acquire(45000); // 45 seconds bright wake
        }

        // 2. Play Alarm Siren Sound immediately at max volume on STREAM_ALARM (bypasses silent mode!)
        try {
            AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
            if (am != null) {
                int maxAlarmVol = am.getStreamMaxVolume(AudioManager.STREAM_ALARM);
                am.setStreamVolume(AudioManager.STREAM_ALARM, maxAlarmVol, 0);
            }

            if (activeMediaPlayer != null) {
                try { activeMediaPlayer.release(); } catch (Exception ignored) {}
            }

            activeMediaPlayer = MediaPlayer.create(this, R.raw.siren);
            if (activeMediaPlayer != null) {
                AudioAttributes audioAttributes = new AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .build();
                activeMediaPlayer.setAudioAttributes(audioAttributes);
                activeMediaPlayer.setLooping(true);
                activeMediaPlayer.start();
            }

            // Start continuous vibration
            activeVibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (activeVibrator != null && activeVibrator.hasVibrator()) {
                long[] pattern = {0, 800, 400, 800, 400, 800};
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    activeVibrator.vibrate(VibrationEffect.createWaveform(pattern, 0));
                } else {
                    activeVibrator.vibrate(pattern, 0);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // 3. Full-Screen Intent for AlarmActivity
        Intent alarmIntent = new Intent(this, AlarmActivity.class);
        alarmIntent.putExtra("level", level);
        alarmIntent.putExtra("reason", reason);
        alarmIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
            this,
            123,
            alarmIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Uri soundUri = Uri.parse(ContentResolver.SCHEME_ANDROID_RESOURCE + "://" + getPackageName() + "/" + R.raw.siren);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_EMERGENCY_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("🚨 EMERGENCY: FLOOD ALERT!")
            .setContentText(reason)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentIntent(fullScreenPendingIntent)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .setSound(soundUri)
            .setAutoCancel(false)
            .setOngoing(true);

        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIF_EMERGENCY_ID, builder.build());
        }

        // Try direct launch
        try {
            startActivity(alarmIntent);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Notification buildForegroundNotification(String statusText) {
        Intent openAppIntent = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        return new NotificationCompat.Builder(this, CHANNEL_MONITOR_ID)
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentIntent(pi)
            .setOngoing(true)
            .setSilent(true)
            .setShowWhen(false)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .build();
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm == null) return;

            // Completely silent/minimized background channel with no status bar icon
            NotificationChannel monitorChannel = new NotificationChannel(
                CHANNEL_MONITOR_ID,
                "Silent Background Monitor",
                NotificationManager.IMPORTANCE_MIN
            );
            monitorChannel.setDescription("Runs secretly in background to check water levels");
            monitorChannel.setShowBadge(false);
            monitorChannel.setSound(null, null);
            monitorChannel.enableLights(false);
            monitorChannel.enableVibration(false);
            monitorChannel.setLockscreenVisibility(Notification.VISIBILITY_SECRET);
            nm.createNotificationChannel(monitorChannel);

            NotificationChannel emergencyChannel = new NotificationChannel(
                CHANNEL_EMERGENCY_ID,
                "Emergency Flood Siren Alarms",
                NotificationManager.IMPORTANCE_HIGH
            );
            emergencyChannel.setDescription("Wakes screen and rings loud siren when alert level passes");
            emergencyChannel.enableLights(true);
            emergencyChannel.enableVibration(true);
            emergencyChannel.setVibrationPattern(new long[]{0, 1000, 500, 1000, 500, 1000});

            Uri soundUri = Uri.parse(ContentResolver.SCHEME_ANDROID_RESOURCE + "://" + getPackageName() + "/" + R.raw.siren);
            AudioAttributes audioAttributes = new AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_ALARM)
                .build();
            emergencyChannel.setSound(soundUri, audioAttributes);
            emergencyChannel.setBypassDnd(true);
            emergencyChannel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);

            nm.createNotificationChannel(emergencyChannel);
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isRunning = false;
        stopActiveSiren(this);
        if (handler != null && pollRunnable != null) {
            handler.removeCallbacks(pollRunnable);
        }
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
