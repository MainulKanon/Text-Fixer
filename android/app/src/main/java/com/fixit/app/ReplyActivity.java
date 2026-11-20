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

/**
 * Opened when the user selects a message they received and picks "Text Fixer Reply".
 * Drafts a reply (optional note + tone); "Copy" puts it on the clipboard to paste into the reply box.
 */
public class ReplyActivity extends Activity {
    private Prefs prefs;
    private String message = "";
    private EditText note, reply;
    private Spinner tone;
    private TextView status;
    private ProgressBar progress;
    private Button generate, copy;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_reply);
        prefs = new Prefs(this);

        CharSequence text = getIntent().getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
        if (text == null) text = getIntent().getCharSequenceExtra(Intent.EXTRA_TEXT);   // "Share → Text Fixer Reply"
        message = text == null ? "" : text.toString().trim();

        ((TextView) findViewById(R.id.message)).setText(message);
        note = findViewById(R.id.note);
        reply = findViewById(R.id.reply);
        tone = findViewById(R.id.tone);
        status = findViewById(R.id.status);
        progress = findViewById(R.id.progress);
        generate = findViewById(R.id.generate);
        copy = findViewById(R.id.copy);

        ArrayAdapter<String> ad = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, Prompts.TONES);
        ad.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        tone.setAdapter(ad);

        findViewById(R.id.close).setOnClickListener(v -> finish());
        generate.setOnClickListener(v -> generate());
        copy.setOnClickListener(v -> {
            String r = reply.getText().toString().trim();
            if (r.isEmpty()) return;
            getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("Text Fixer reply", r));
            Toast.makeText(this, R.string.reply_copied, Toast.LENGTH_LONG).show();
            finish();
        });

        if (message.isEmpty()) {
            setStatus(getString(R.string.no_text), true);
        } else if (!prefs.hasAnyKey()) {
            setStatus(getString(R.string.no_key), true);
            generate.setText(R.string.open_settings);
            generate.setOnClickListener(v -> {
                startActivity(new Intent(this, MainActivity.class));
                finish();
            });
        } else {
            generate();   // draft right away; the user can add a note and regenerate
        }
    }

    private void generate() {
        int t = tone.getSelectedItemPosition();
        String system = Prompts.REPLY_PROMPT + "\n\n" + Prompts.TONE_HINTS[Math.max(0, t)];
        String user = "Message I received:\n<<<\n" + message + "\n>>>";
        String n = note.getText().toString().trim();
        if (!n.isEmpty()) user += "\n\nWhat I want to say in my reply (use this): " + n;
        setBusy(true);
        final String u = user;
        Bg.run(this, () -> Ai.run(prefs, system, u), r -> {
            reply.setText(r.text);
            setBusy(false);
            setStatus(getString(R.string.reply_done, r.provider), false);
        }, e -> {
            setBusy(false);
            setStatus(e, true);
        });
    }

    private void setBusy(boolean busy) {
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        generate.setEnabled(!busy);
        copy.setEnabled(!busy && reply.length() > 0);
        if (busy) setStatus(getString(R.string.writing_reply), false);
        else generate.setText(R.string.regenerate);
    }

    private void setStatus(String s, boolean isError) {
        status.setText(s);
        status.setTextColor(getColor(isError ? R.color.error : R.color.muted));
    }
}
