package com.rivernet.alarm;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.android.material.button.MaterialButton;

import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    private TextView tvCurrentLevel;
    private TextView tvTrend;
    private TextView tvLastCheck;
    private TextView tvServiceStatus;
    private MaterialButton btnToggleService;
    private MaterialButton btnCloseApp;
    private MaterialButton btnTestAlarmNow;
    private MaterialButton btnTestAlarmDelay;
    private MaterialButton btnOverlayOpt;
    private MaterialButton btnHideNotif;
    private MaterialButton btnBatteryOpt;

    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            updateUI();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvCurrentLevel = findViewById(R.id.tvCurrentLevel);
        tvTrend = findViewById(R.id.tvTrend);
        tvLastCheck = findViewById(R.id.tvLastCheck);
        tvServiceStatus = findViewById(R.id.tvServiceStatus);
        btnToggleService = findViewById(R.id.btnToggleService);
        btnCloseApp = findViewById(R.id.btnCloseApp);
        btnTestAlarmNow = findViewById(R.id.btnTestAlarmNow);
        btnTestAlarmDelay = findViewById(R.id.btnTestAlarmDelay);
        btnOverlayOpt = findViewById(R.id.btnOverlayOpt);
        btnHideNotif = findViewById(R.id.btnHideNotif);
        btnBatteryOpt = findViewById(R.id.btnBatteryOpt);

        requestPermissionsIfNeeded();
        startMonitorService();
        updateUI();

        btnToggleService.setOnClickListener(v -> {
            startMonitorService();
            Toast.makeText(this, "River Monitor Started!", Toast.LENGTH_SHORT).show();
            updateUI();
        });

        // Require PIN before stopping the app / background service
        btnCloseApp.setOnClickListener(v -> promptPinToStopService());

        btnTestAlarmNow.setOnClickListener(v -> {
            Intent testIntent = new Intent(this, RiverMonitorService.class);
            testIntent.setAction(RiverMonitorService.ACTION_TEST_NOW);
            startService(testIntent);
        });

        btnTestAlarmDelay.setOnClickListener(v -> {
            Intent testIntent = new Intent(this, RiverMonitorService.class);
            testIntent.setAction(RiverMonitorService.ACTION_TEST_DELAYED);
            startService(testIntent);
            Toast.makeText(this, "Lock phone NOW! Siren will sound in 5s.", Toast.LENGTH_LONG).show();
        });

        btnOverlayOpt.setOnClickListener(v -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                if (!Settings.canDrawOverlays(this)) {
                    Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                } else {
                    Toast.makeText(this, "Display over apps permission is already granted!", Toast.LENGTH_SHORT).show();
                }
            }
        });

        btnHideNotif.setOnClickListener(v -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Intent intent = new Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS);
                intent.putExtra(Settings.EXTRA_APP_PACKAGE, getPackageName());
                intent.putExtra(Settings.EXTRA_CHANNEL_ID, RiverMonitorService.CHANNEL_MONITOR_ID);
                try {
                    startActivity(intent);
                } catch (Exception e) {
                    Intent appIntent = new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                    appIntent.putExtra(Settings.EXTRA_APP_PACKAGE, getPackageName());
                    startActivity(appIntent);
                }
            } else {
                Toast.makeText(this, "Silent background channel is already hidden!", Toast.LENGTH_SHORT).show();
            }
        });

        btnBatteryOpt.setOnClickListener(v -> requestIgnoreBatteryOptimizations());
    }

    private void promptPinToStopService() {
        if (PinManager.isLockedOut(this)) {
            long remaining = PinManager.getRemainingLockoutSeconds(this);
            Toast.makeText(this, "⛔ System Locked! Too many failed attempts. Try again in " + remaining + "s.", Toast.LENGTH_LONG).show();
            return;
        }

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("🔒 Enter PIN to Stop Monitor");
        builder.setMessage("Enter secret PIN to stop background monitoring:");

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        input.setGravity(Gravity.CENTER);
        input.setTextSize(22);
        input.setHint("••••");

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(50, 20, 50, 20);
        input.setLayoutParams(params);
        container.addView(input);
        builder.setView(container);

        builder.setPositiveButton("Verify & Stop", (dialog, which) -> {
            String entered = input.getText().toString();
            if (PinManager.verifyPin(this, entered)) {
                Intent stopIntent = new Intent(this, RiverMonitorService.class);
                stopIntent.setAction(RiverMonitorService.ACTION_STOP_SERVICE);
                startService(stopIntent);
                Toast.makeText(this, "✅ River Monitor Stopped", Toast.LENGTH_SHORT).show();
                finishAffinity();
            } else {
                if (PinManager.isLockedOut(this)) {
                    Toast.makeText(this, "⛔ 3 Failed Attempts! System locked for 1 minute.", Toast.LENGTH_LONG).show();
                } else {
                    int fails = PinManager.getFailedAttempts(this);
                    Toast.makeText(this, "❌ Incorrect PIN! (" + fails + "/3 attempts)", Toast.LENGTH_LONG).show();
                }
            }
        });

        builder.setNegativeButton("Cancel", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    private void updateUI() {
        if (RiverMonitorService.latestLevel > 0) {
            tvCurrentLevel.setText(String.format(Locale.US, "%.2f m", RiverMonitorService.latestLevel));
            tvTrend.setText(RiverMonitorService.latestTrend);
            tvLastCheck.setText(String.format("Last checked: %s", RiverMonitorService.lastCheckTime));
        } else {
            tvCurrentLevel.setText("Loading...");
            tvTrend.setText("Connecting to RiverNet LK...");
        }

        if (RiverMonitorService.isRunning) {
            tvServiceStatus.setText("Status: ACTIVE (Monitoring 24/7)");
            tvServiceStatus.setTextColor(0xFF4ADE80);
        } else {
            tvServiceStatus.setText("Status: STOPPED / CLOSED");
            tvServiceStatus.setTextColor(0xFFF87171);
        }
    }

    private void startMonitorService() {
        Intent serviceIntent = new Intent(this, RiverMonitorService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void requestPermissionsIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, 101);
            }
        }
    }

    @SuppressLint("BatteryLife")
    private void requestIgnoreBatteryOptimizations() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                intent.setData(Uri.parse("package:" + getPackageName()));
                startActivity(intent);
            } else {
                Toast.makeText(this, "Battery optimization already disabled!", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statusReceiver, new IntentFilter(RiverMonitorService.BROADCAST_STATUS), Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(statusReceiver, new IntentFilter(RiverMonitorService.BROADCAST_STATUS));
        }
        updateUI();
    }

    @Override
    protected void onPause() {
        super.onPause();
        try {
            unregisterReceiver(statusReceiver);
        } catch (Exception ignored) {}
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 101 && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Notification permission granted!", Toast.LENGTH_SHORT).show();
        }
    }
}
