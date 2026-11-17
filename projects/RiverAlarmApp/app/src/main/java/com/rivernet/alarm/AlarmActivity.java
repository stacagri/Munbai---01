package com.rivernet.alarm;

import android.app.KeyguardManager;
import android.content.Context;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.button.MaterialButton;

import java.util.Locale;

public class AlarmActivity extends AppCompatActivity {

    private boolean isPinAuthenticated = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
            if (km != null) {
                km.requestDismissKeyguard(this, null);
            }
        } else {
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            );
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_alarm);

        double level = getIntent().getDoubleExtra("level", 5.48);
        String reason = getIntent().getStringExtra("reason");

        TextView tvAlarmLevel = findViewById(R.id.tvAlarmLevel);
        TextView tvAlarmDetails = findViewById(R.id.tvAlarmDetails);
        MaterialButton btnStopAlarm = findViewById(R.id.btnStopAlarm);
        MaterialButton btnSnoozeAlarm = findViewById(R.id.btnSnoozeAlarm);

        tvAlarmLevel.setText(String.format(Locale.US, "%.2f m", level));
        if (reason != null && !reason.isEmpty()) {
            tvAlarmDetails.setText(reason);
        }

        btnStopAlarm.setOnClickListener(v -> showPinDialog(60));
        btnSnoozeAlarm.setOnClickListener(v -> showPinDialog(15));
    }

    private void showPinDialog(int snoozeMinutes) {
        if (PinManager.isLockedOut(this)) {
            long remaining = PinManager.getRemainingLockoutSeconds(this);
            Toast.makeText(this, "⛔ System Locked! Too many failed attempts. Try again in " + remaining + "s.", Toast.LENGTH_LONG).show();
            return;
        }

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("🔒 Security PIN Required");
        builder.setMessage("Enter PIN to silence the emergency flood siren:");

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        input.setGravity(Gravity.CENTER);
        input.setTextSize(24);
        input.setHint("••••");

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(50, 20, 50, 20);
        input.setLayoutParams(params);
        container.addView(input);
        builder.setView(container);

        builder.setPositiveButton("Verify & Silence", (dialog, which) -> {
            String enteredPin = input.getText().toString();
            if (PinManager.verifyPin(this, enteredPin)) {
                isPinAuthenticated = true;
                RiverMonitorService.setSnoozeMinutes(snoozeMinutes);
                RiverMonitorService.stopActiveSiren(this);
                Toast.makeText(this, "✅ Siren Silenced & Acknowledged", Toast.LENGTH_SHORT).show();
                finish();
            } else {
                if (PinManager.isLockedOut(this)) {
                    Toast.makeText(this, "⛔ 3 Failed Attempts! System locked for 1 minute. Siren will continue blaring.", Toast.LENGTH_LONG).show();
                } else {
                    int fails = PinManager.getFailedAttempts(this);
                    Toast.makeText(this, "❌ Incorrect PIN! (" + fails + "/3 attempts)", Toast.LENGTH_LONG).show();
                }
            }
        });

        builder.setNegativeButton("Cancel", (dialog, which) -> dialog.cancel());

        AlertDialog dialog = builder.create();
        dialog.setCanceledOnTouchOutside(false);
        dialog.show();
    }

    @Override
    public void onBackPressed() {
        showPinDialog(60);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isPinAuthenticated) {
            RiverMonitorService.stopActiveSiren(this);
        }
    }
}
