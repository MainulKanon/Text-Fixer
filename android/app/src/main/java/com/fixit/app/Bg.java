package com.fixit.app;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;

/**
 * Runs one network job on a short-lived thread and delivers the result on the UI thread.
 * No thread pool is kept alive, so nothing lingers once the screen closes.
 */
final class Bg {
    private Bg() {}

    interface Job<T> { T run() throws Exception; }
    interface Done<T> { void ok(T value); }
    interface Fail { void error(String message); }

    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    static <T> void run(Activity owner, Job<T> job, Done<T> done, Fail fail) {
        Thread t = new Thread(() -> {
            T value = null;
            String err = null;
            try {
                value = job.run();
            } catch (Exception e) {
                err = e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName();
            }
            final T v = value;
            final String e2 = err;
            MAIN.post(() -> {
                if (owner.isFinishing() || owner.isDestroyed()) return;   // screen already closed
                if (e2 != null) fail.error(e2); else done.ok(v);
            });
        }, "fixit-ai");
        t.setDaemon(true);
        t.start();
    }
}
