package com.fixit.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

/** Settings: API keys, models, primary provider, main prompt, and a Test button. */
public class MainActivity extends Activity {
    private Prefs prefs;
    private final EditText[] keys = new EditText[Prefs.PROVIDERS.length];
    private final EditText[] models = new EditText[Prefs.PROVIDERS.length];
    private Spinner primary;
    private EditText prompt;
    private TextView testResult;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        prefs = new Prefs(this);

        LinearLayout list = findViewById(R.id.providers);
        for (int i = 0; i < Prefs.PROVIDERS.length; i++) list.addView(providerCard(i));

        primary = findViewById(R.id.primary);
        ArrayAdapter<String> ad = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, Prefs.LABELS);
        ad.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        primary.setAdapter(ad);
        primary.setSelection(Prefs.index(prefs.primary()));

        prompt = findViewById(R.id.prompt);
        prompt.setText(prefs.mainPrompt());
        testResult = findViewById(R.id.test_result);

        findViewById(R.id.save).setOnClickListener(v -> {
            save();
            Toast.makeText(this, R.string.saved, Toast.LENGTH_SHORT).show();
        });
        findViewById(R.id.test).setOnClickListener(v -> test());
        findViewById(R.id.reset_prompt).setOnClickListener(v -> prompt.setText(Prompts.DEFAULT_SYSTEM_PROMPT));
    }

    private View providerCard(int i) {
        View card = getLayoutInflater().inflate(R.layout.item_provider, (ViewGroup) findViewById(R.id.providers), false);
        ((TextView) card.findViewById(R.id.name)).setText(Prefs.LABELS[i]);
        keys[i] = card.findViewById(R.id.key);
        models[i] = card.findViewById(R.id.model);
        String p = Prefs.PROVIDERS[i];
        keys[i].setText(prefs.key(p));
        keys[i].setTypeface(Typeface.DEFAULT);   // password fields default to a monospace font
        models[i].setText(prefs.model(p));
        Button show = card.findViewById(R.id.show);
        show.setOnClickListener(v -> {
            boolean hidden = (keys[i].getInputType() & InputType.TYPE_MASK_VARIATION)
                    == InputType.TYPE_TEXT_VARIATION_PASSWORD;
            keys[i].setInputType(InputType.TYPE_CLASS_TEXT | (hidden ? InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                    : InputType.TYPE_TEXT_VARIATION_PASSWORD));
            keys[i].setTypeface(Typeface.DEFAULT);
            keys[i].setSelection(keys[i].length());
            show.setText(hidden ? R.string.hide : R.string.show);
        });
        card.findViewById(R.id.get_key).setOnClickListener(v ->
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(Prefs.KEY_URLS[i]))));
        if (i == 0) ((TextView) card.findViewById(R.id.hint)).setText(R.string.groq_hint);
        return card;
    }

    private void save() {
        for (int i = 0; i < Prefs.PROVIDERS.length; i++) {
            prefs.setKey(Prefs.PROVIDERS[i], keys[i].getText().toString());
            prefs.setModel(Prefs.PROVIDERS[i], models[i].getText().toString());
        }
        prefs.setPrimary(Prefs.PROVIDERS[primary.getSelectedItemPosition()]);
        String pr = prompt.getText().toString().trim();
        prefs.setMainPrompt(pr.isEmpty() ? Prompts.DEFAULT_SYSTEM_PROMPT : pr);
    }

    private void test() {
        save();
        testResult.setTextColor(getColor(R.color.muted));
        testResult.setText(R.string.testing);
        Bg.run(this, () -> Ai.run(prefs, Prompts.forMode(Prompts.FIX, prefs.mainPrompt()),
                "i has send you the file yesterday, pls check it"), r -> {
            // A retired model may have been swapped for a working one: refresh the fields.
            for (int i = 0; i < Prefs.PROVIDERS.length; i++) models[i].setText(prefs.model(Prefs.PROVIDERS[i]));
            testResult.setTextColor(getColor(R.color.ok));
            testResult.setText(getString(R.string.test_ok, r.provider, r.text));
        }, e -> {
            testResult.setTextColor(getColor(R.color.error));
            testResult.setText(e);
        });
    }
}
