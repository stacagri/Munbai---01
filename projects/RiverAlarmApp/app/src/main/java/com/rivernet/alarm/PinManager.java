package com.rivernet.alarm;

import android.content.Context;
import android.content.SharedPreferences;

public class PinManager {

    private static final String PREF_NAME = "river_alert_security_prefs";
    private static final String KEY_FAILED_ATTEMPTS = "failed_attempts";
    private static final String KEY_LOCKOUT_UNTIL = "lockout_until";
    private static final String SECRET_PIN = "5555";

    public static boolean isLockedOut(Context context) {
        return getRemainingLockoutSeconds(context) > 0;
    }

    public static long getRemainingLockoutSeconds(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        long lockoutUntil = prefs.getLong(KEY_LOCKOUT_UNTIL, 0);
        long diff = lockoutUntil - System.currentTimeMillis();
        return diff > 0 ? (diff / 1000) + 1 : 0;
    }

    public static int getFailedAttempts(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        return prefs.getInt(KEY_FAILED_ATTEMPTS, 0);
    }

    public static boolean verifyPin(Context context, String input) {
        if (isLockedOut(context)) {
            return false;
        }

        SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        if (input != null && SECRET_PIN.equals(input.trim())) {
            // Success: reset failures and lockout
            prefs.edit()
                .putInt(KEY_FAILED_ATTEMPTS, 0)
                .putLong(KEY_LOCKOUT_UNTIL, 0)
                .apply();
            return true;
        } else {
            // Failure: increment failure count
            int fails = prefs.getInt(KEY_FAILED_ATTEMPTS, 0) + 1;
            SharedPreferences.Editor editor = prefs.edit();
            if (fails >= 3) {
                // Lockout for 60 seconds (1 minute)
                editor.putLong(KEY_LOCKOUT_UNTIL, System.currentTimeMillis() + 60_000L);
                editor.putInt(KEY_FAILED_ATTEMPTS, 0);
            } else {
                editor.putInt(KEY_FAILED_ATTEMPTS, fails);
            }
            editor.apply();
            return false;
        }
    }
}
