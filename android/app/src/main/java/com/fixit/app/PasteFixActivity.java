package com.fixit.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;

/**
 * Paste & fix: the app's main screen. Paste (or share) any text, pick a style, get the improved
 * version to copy. Like the rest of the app, nothing runs once this screen is closed.
 */
public class PasteFixActivity extends Activity {
    private Prefs prefs;
    private EditText input;
    private Spinner style;
    private Button fix, copy, retry, share, edit;
    private TextView result, status;
    private View resultCard, keyBanner;
    private ProgressBar progress;
    private final ArrayList<String> modes = new ArrayList<>(Prompts.MODES.keySet());

    private String original = "";
    private String fixed = "";
    private boolean busy;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_paste);
        prefs = new Prefs(this);

        input = findViewById(R.id.input);
        style = findViewById(R.id.style);
        fix = findViewById(R.id.fix);
        copy = findViewById(R.id.copy);
        retry = findViewById(R.id.retry);
        share = findViewById(R.id.share);
        edit = findViewById(R.id.edit);
        result = findViewById(R.id.result);
        status = findViewById(R.id.status);
        resultCard = findViewById(R.id.result_card);
        keyBanner = findViewById(R.id.key_banner);
        progress = findViewById(R.id.progress);

        ArrayAdapter<String> ad = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        ad.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        style.setAdapter(ad);

        findViewById(R.id.settings).setOnClickListener(v -> startActivity(new Intent(this, MainActivity.class)));
        findViewById(R.id.add_key).setOnClickListener(v -> startActivity(new Intent(this, MainActivity.class)));
        findViewById(R.id.paste).setOnClickListener(v -> pasteClipboard());
        findViewById(R.id.clear).setOnClickListener(v -> {
            input.setText("");
            clearResult();
            input.requestFocus();
        });
        fix.setOnClickListener(v -> fix(false));
        // Client messages often can't be selected (e.g. Fiverr chat bubbles), so: copy → paste here → Reply.
        findViewById(R.id.reply).setOnClickListener(v -> {
            String text = input.getText().toString().trim();
            if (text.isEmpty()) {
                setStatus(getString(R.string.paste_message_first), true);
                return;
            }
            startActivity(new Intent(this, ReplyActivity.class)
                    .putExtra(Intent.EXTRA_PROCESS_TEXT, text)
                    .putExtra(Intent.EXTRA_PROCESS_TEXT_READONLY, true));
        });
        retry.setOnClickListener(v -> fix(true));
        copy.setOnClickListener(v -> {
            getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("Text Fixer", fixed));
            Toast.makeText(this, R.string.copied_paste, Toast.LENGTH_SHORT).show();
        });
        share.setOnClickListener(v -> startActivity(Intent.createChooser(
                new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, fixed), null)));
        edit.setOnClickListener(v -> {
            input.setText(fixed);
            input.setSelection(input.length());
            clearResult();
            input.requestFocus();
        });

        if (state != null) {
            original = state.getString("original", "");
            fixed = state.getString("fixed", "");
            if (!fixed.isEmpty()) showResult(state.getString("provider", ""));
        }
        handleShare(getIntent());
        refreshButtons();
    }

    @Override
    protected void onResume() {
        super.onResume();
        keyBanner.setVisibility(prefs.hasAnyKey() ? View.GONE : View.VISIBLE);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleShare(intent);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putString("original", original);
        out.putString("fixed", fixed);
        out.putString("provider", String.valueOf(status.getTag() == null ? "" : status.getTag()));
    }

    /** "Share → Text Fixer" from any app: fill the box and fix right away. */
    private void handleShare(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        CharSequence shared = intent.getCharSequenceExtra(Intent.EXTRA_TEXT);
        if (shared == null || shared.toString().trim().isEmpty()) return;
        input.setText(shared.toString().trim());
        intent.setAction(Intent.ACTION_MAIN);   // don't re-run on rotation
        if (prefs.hasAnyKey()) fix(false);
    }

    private void pasteClipboard() {
        ClipboardManager cm = getSystemService(ClipboardManager.class);
        ClipData clip = cm.getPrimaryClip();
        if (clip == null || clip.getItemCount() == 0) {
            setStatus(getString(R.string.clipboard_empty), true);
            return;
        }
        CharSequence t = clip.getItemAt(0).coerceToText(this);
        input.setText(t);
        input.setSelection(input.length());
        clearResult();
    }

    private void fix(boolean alternative) {
        String text = input.getText().toString().trim();
        if (busy) return;
        if (text.isEmpty()) {
            setStatus(getString(R.string.paste_first), true);
            return;
        }
        if (!prefs.hasAnyKey()) {
            setStatus(getString(R.string.no_key), true);
            return;
        }
        String mode = modes.get(Math.max(0, style.getSelectedItemPosition()));
        String system = Prompts.forMode(mode, prefs.mainPrompt());
        if (alternative && !fixed.isEmpty() && text.equals(original)) {
            system += String.format(Prompts.ALTERNATIVE_HINT, fixed);
        }
        original = text;
        busy = true;
        refreshButtons();
        setStatus(getString(R.string.working, mode), false);
        final String sys = system;
        Bg.run(this, () -> Ai.run(prefs, sys, text), r -> {
            busy = false;
            fixed = r.text;
            showResult(r.provider);
            refreshButtons();
        }, e -> {
            busy = false;
            setStatus(e, true);
            refreshButtons();
        });
    }

    private void showResult(String provider) {
        result.setText(Diff.highlight(original, fixed, getColor(R.color.added_bg), getColor(R.color.added_fg)));
        resultCard.setVisibility(View.VISIBLE);
        status.setTag(provider);
        boolean same = fixed.trim().equals(original.trim());
        setStatus(same ? getString(R.string.looks_good, provider) : getString(R.string.done_via, provider), false);
    }

    private void clearResult() {
        fixed = "";
        resultCard.setVisibility(View.GONE);
        setStatus("", false);
        refreshButtons();
    }

    private void refreshButtons() {
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        fix.setEnabled(!busy);
        fix.setText(busy ? R.string.working_short : R.string.fix);
        boolean has = !fixed.isEmpty() && !busy;
        for (Button b : new Button[]{copy, retry, share, edit}) b.setEnabled(has);
    }

    private void setStatus(String s, boolean isError) {
        status.setText(s);
        status.setVisibility(s.isEmpty() ? View.GONE : View.VISIBLE);
        status.setTextColor(getColor(isError ? R.color.error : R.color.muted));
    }
}
