package com.carlos.kwaibridge;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.TextUtils;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String PREFS = "kwai_bridge";
    private TextView statusView;
    private Switch enabledSwitch;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private final Runnable statusRefresh = new Runnable() {
        @Override
        public void run() {
            refreshStatus();
            handler.postDelayed(this, 2000L);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int pad = dp(20);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Carlos Kwai Bridge");
        title.setTextSize(28f);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView description = new TextView(this);
        description.setText("Ponte local entre a automação Carlos Reels e o app oficial do Kwai. Ela só age quando existe um vídeo novo preparado e nunca lê senha, mensagens ou contatos.");
        description.setTextSize(16f);
        LinearLayout.LayoutParams descriptionParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        descriptionParams.topMargin = dp(12);
        root.addView(description, descriptionParams);

        enabledSwitch = new Switch(this);
        enabledSwitch.setText("Publicação automática");
        enabledSwitch.setTextSize(18f);
        enabledSwitch.setChecked(prefs().getBoolean("enabled", false));
        enabledSwitch.setOnCheckedChangeListener((buttonView, isChecked) -> {
            prefs().edit().putBoolean("enabled", isChecked).apply();
            prefs().edit().putString("last_status", isChecked
                    ? "Automação ativada. Verificando a fila do Kwai."
                    : "Automação pausada no celular.").apply();
            if (isChecked) {
                KwaiAccessibilityService.requestImmediatePoll();
            }
            refreshStatus();
        });
        LinearLayout.LayoutParams switchParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        switchParams.topMargin = dp(22);
        root.addView(enabledSwitch, switchParams);

        Button accessibilityButton = new Button(this);
        accessibilityButton.setText("1. Ativar acessibilidade");
        accessibilityButton.setOnClickListener(v -> {
            Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
            startActivity(intent);
        });
        root.addView(accessibilityButton, buttonParams());

        Button kwaiButton = new Button(this);
        kwaiButton.setText("2. Abrir o Kwai e confirmar login");
        kwaiButton.setOnClickListener(v -> {
            Intent launch = getPackageManager().getLaunchIntentForPackage("com.kwai.video");
            if (launch != null) startActivity(launch);
        });
        root.addView(kwaiButton, buttonParams());

        Button testButton = new Button(this);
        testButton.setText("3. Testar pacote agora");
        testButton.setOnClickListener(v -> {
            prefs().edit().putBoolean("enabled", true).apply();
            enabledSwitch.setChecked(true);
            boolean requested = KwaiAccessibilityService.requestImmediatePoll();
            prefs().edit().putString("last_status", requested
                    ? "Teste solicitado."
                    : "Ative a acessibilidade primeiro; depois toque novamente em testar.").apply();
            refreshStatus();
        });
        root.addView(testButton, buttonParams());

        statusView = new TextView(this);
        statusView.setTextSize(15f);
        statusView.setTextIsSelectable(true);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        statusParams.topMargin = dp(22);
        root.addView(statusView, statusParams);

        TextView note = new TextView(this);
        note.setText("Deixe o Kwai instalado e logado. No Samsung, também coloque este app em Bateria > Sem restrições. A ponte verifica a fila a cada 3 minutos e só abre o Kwai quando aparece um novo pacote.");
        note.setTextSize(14f);
        LinearLayout.LayoutParams noteParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        noteParams.topMargin = dp(18);
        root.addView(note, noteParams);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);
    }

    private LinearLayout.LayoutParams buttonParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = dp(12);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private boolean isAccessibilityEnabled() {
        ComponentName component = new ComponentName(this, KwaiAccessibilityService.class);
        String expected = component.flattenToString();
        String enabled = Settings.Secure.getString(
                getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        TextUtils.SimpleStringSplitter splitter = new TextUtils.SimpleStringSplitter(':');
        splitter.setString(enabled);
        for (String value : splitter) {
            if (expected.equalsIgnoreCase(value)) return true;
        }
        return false;
    }

    private boolean isKwaiInstalled() {
        try {
            getPackageManager().getPackageInfo("com.kwai.video", 0);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    private void refreshStatus() {
        SharedPreferences p = prefs();
        StringBuilder builder = new StringBuilder();
        builder.append("Acessibilidade: ").append(isAccessibilityEnabled() ? "ATIVA" : "DESATIVADA").append('\n');
        builder.append("Kwai oficial: ").append(isKwaiInstalled() ? "INSTALADO" : "NÃO ENCONTRADO").append('\n');
        builder.append("Automação: ").append(p.getBoolean("enabled", false) ? "ATIVA" : "PAUSADA").append('\n');
        String pending = p.getString("pending_run", "");
        if (!pending.isEmpty()) builder.append("Pacote pendente: ").append(pending).append('\n');
        String last = p.getString("last_run", "");
        if (!last.isEmpty()) builder.append("Último pacote concluído: ").append(last).append('\n');
        builder.append("\nStatus: ").append(p.getString("last_status", "Aguardando configuração inicial."));
        if (statusView != null) statusView.setText(builder.toString());
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.removeCallbacks(statusRefresh);
        handler.post(statusRefresh);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(statusRefresh);
        super.onPause();
    }
}
