package com.fixit.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.View;
import android.widget.Button;
import android.widget.PopupMenu;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Opened by Android when the user picks "Text Fixer" in the text-selection menu.
 * Shows a preview of the fixed text; "Replace" hands it back to the app, which swaps the selection.
 * Nothing runs before or after this screen.
 */
public class FixActivity extends Activity {
    private Prefs prefs;
    private String original = "";
    private String fixed = "";
    private String mode = Prompts.FIX;
    private boolean readOnly;

    private TextView title, before, result, error;
    private ProgressBar progress;
    private Button replace, retry, style, copy;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_fix);
        setFinishOnTouchOutside(true);
        prefs = new Prefs(this);

        CharSequence text = getIntent().getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
        original = text == null ? "" : text.toString();
        readOnly = getIntent().getBooleanExtra(Intent.EXTRA_PROCESS_TEXT_READONLY, false);

        title = findViewById(R.id.title);
        before = findViewById(R.id.before);
        result = findViewById(R.id.result);
        error = findViewById(R.id.error);
        progress = findViewById(R.id.progress);
        replace = findViewById(R.id.replace);
        retry = findViewById(R.id.retry);
        style = findViewById(R.id.style);
        copy = findViewById(R.id.copy);

        findViewById(R.id.close).setOnClickListener(v -> finish());
        replace.setVisibility(readOnly ? View.GONE : View.VISIBLE);   // e.g. text selected on a web page
        replace.setOnClickListener(v -> {
            setResult(RESULT_OK, new Intent().putExtra(Intent.EXTRA_PROCESS_TEXT, fixed));
            finish();
        });
        retry.setOnClickListener(v -> fix(mode, true));
        style.setOnClickListener(this::showStyles);
        copy.setOnClickListener(v -> {
            ClipboardManager cm = getSystemService(ClipboardManager.class);
            cm.setPrimaryClip(ClipData.newPlainText("Text Fixer", fixed));
            Toast.makeText(this, R.string.copied, Toast.LENGTH_SHORT).show();
            finish();
        });
        before.setText(original);

        if (original.trim().isEmpty()) {
            showError(getString(R.string.no_text));
        } else if (!prefs.hasAnyKey()) {
            showError(getString(R.string.no_key));
            replace.setVisibility(View.GONE);
            style.setVisibility(View.GONE);
            copy.setVisibility(View.GONE);
            retry.setText(R.string.open_settings);
            retry.setEnabled(true);
            retry.setOnClickListener(v -> {
                startActivity(new Intent(this, MainActivity.class));
                finish();
            });
        } else {
            fix(Prompts.FIX, false);
        }
    }

    private void fix(String newMode, boolean alternative) {
        mode = newMode;
        String system = Prompts.forMode(mode, prefs.mainPrompt());
        if (alternative && !fixed.isEmpty()) system += String.format(Prompts.ALTERNATIVE_HINT, fixed);
        setBusy(true);
        final String sys = system;
        Bg.run(this, () -> Ai.run(prefs, sys, original), r -> {
            fixed = r.text;
            title.setText(getString(R.string.title_fmt, mode, r.provider));
            result.setText(Diff.highlight(original, fixed, getColor(R.color.added_bg), getColor(R.color.added_fg)));
            result.setVisibility(View.VISIBLE);
            error.setVisibility(View.GONE);
            setBusy(false);
            if (fixed.trim().equals(original.trim())) {
                title.setText(getString(R.string.looks_good, r.provider));
            }
        }, this::showError);
    }

    private void showStyles(View anchor) {
        PopupMenu menu = new PopupMenu(this, anchor);
        int id = 0;
        for (String name : Prompts.MODES.keySet()) {
            menu.getMenu().add(Menu.NONE, id++, Menu.NONE, name).setEnabled(!name.equals(mode) || fixed.isEmpty());
        }
        menu.setOnMenuItemClickListener(item -> {
            fix(item.getTitle().toString(), false);
            return true;
        });
        menu.show();
    }

    private void setBusy(boolean busy) {
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        if (busy) {
            title.setText(getString(R.string.working, mode));
            error.setVisibility(View.GONE);
        }
        boolean hasResult = !fixed.isEmpty();
        replace.setEnabled(!busy && hasResult);
        copy.setEnabled(!busy && hasResult);
        retry.setEnabled(!busy);
        style.setEnabled(!busy);
    }

    private void showError(String message) {
        setBusy(false);
        title.setText(R.string.app_name);
        error.setText(message);
        error.setVisibility(View.VISIBLE);
    }
}
