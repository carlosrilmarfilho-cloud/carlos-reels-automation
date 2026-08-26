package com.carlos.kwaibridge;

import android.accessibilityservice.AccessibilityService;
import android.content.ClipData;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public class KwaiAccessibilityService extends AccessibilityService {
    private static final String PREFS = "kwai_bridge";
    private static final String BASE = "https://raw.githubusercontent.com/carlosrilmarfilho-cloud/carlos-reels-automation/media-host-kwai/";
    private static final long POLL_MS = 180_000L;
    private static final long UI_COOLDOWN_MS = 1_600L;
    private static volatile KwaiAccessibilityService instance;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean polling = new AtomicBoolean(false);
    private final AtomicBoolean uiScheduled = new AtomicBoolean(false);
    private volatile boolean stopped = false;
    private Thread pollThread;
    private long lastUiActionAt = 0L;

    private static final List<String> NEXT_LABELS = Arrays.asList(
            "próximo", "proximo", "next", "avançar", "avancar", "continuar", "continue"
    );
    private static final List<String> PUBLISH_LABELS = Arrays.asList(
            "compartilhar", "share", "publicar", "postar", "publish", "post", "publicar agora"
    );

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        stopped = false;
        setStatus("Acessibilidade ativa. Monitorando a fila do Kwai.");
        startPollingLoop();
    }

    public static boolean requestImmediatePoll() {
        KwaiAccessibilityService service = instance;
        if (service == null) return false;
        service.pollAsync();
        return true;
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private void setStatus(String value) {
        prefs().edit().putString("last_status", value).apply();
    }

    private void startPollingLoop() {
        if (pollThread != null && pollThread.isAlive()) return;
        pollThread = new Thread(() -> {
            while (!stopped) {
                try {
                    pollOnce();
                } catch (Throwable error) {
                    setStatus("Erro ao verificar fila: " + safeMessage(error));
                }
                try {
                    Thread.sleep(POLL_MS);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }, "kwai-bridge-poller");
        pollThread.start();
    }

    private void pollAsync() {
        new Thread(() -> {
            try {
                pollOnce();
            } catch (Throwable error) {
                setStatus("Erro no teste: " + safeMessage(error));
            }
        }, "kwai-bridge-poll-now").start();
    }

    private void pollOnce() throws Exception {
        if (!prefs().getBoolean("enabled", false)) return;
        if (!polling.compareAndSet(false, true)) return;
        try {
            String runId = readText(BASE + "run-id.txt?ts=" + System.currentTimeMillis()).trim();
            if (runId.isEmpty()) {
                setStatus("Fila do Kwai ainda não tem pacote disponível.");
                return;
            }
            String lastRun = prefs().getString("last_run", "");
            String pendingRun = prefs().getString("pending_run", "");
            if (runId.equals(lastRun)) {
                setStatus("Fila em dia. Último pacote: " + runId);
                return;
            }
            if (runId.equals(pendingRun)) {
                setStatus("Pacote " + runId + " ainda está pendente no Kwai.");
                return;
            }

            setStatus("Novo pacote " + runId + " encontrado. Baixando vídeo.");
            String payloadText = readText(BASE + "latest.json?run=" + runId);
            JSONObject payload = new JSONObject(payloadText);
            String caption = payload.optString("caption", "").trim();
            Uri videoUri = downloadVideo(runId);

            SharedPreferences.Editor editor = prefs().edit();
            editor.putString("pending_run", runId);
            editor.putString("pending_caption", caption);
            editor.putString("pending_uri", videoUri.toString());
            editor.putString("stage", "launching");
            editor.putInt("ui_click_count", 0);
            editor.remove("confirm_attempts");
            editor.putLong("pending_started_at", System.currentTimeMillis());
            editor.apply();

            setStatus("Vídeo pronto. Abrindo o Kwai para publicar o pacote " + runId + ".");
            mainHandler.post(() -> launchKwaiShare(videoUri, caption));
        } finally {
            polling.set(false);
        }
    }

    private Uri downloadVideo(String runId) throws Exception {
        ContentResolver resolver = getContentResolver();
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.DISPLAY_NAME, "kwai_" + runId + ".mp4");
        values.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        values.put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/CarlosKwaiBridge");
        values.put(MediaStore.Video.Media.IS_PENDING, 1);
        Uri uri = resolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("Android não criou o arquivo do vídeo");

        HttpURLConnection connection = null;
        try {
            URL url = new URL(BASE + "latest.mp4?run=" + runId);
            connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(20_000);
            connection.setReadTimeout(120_000);
            connection.setRequestProperty("User-Agent", "CarlosKwaiBridge/1.0");
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                throw new IllegalStateException("download HTTP " + status);
            }
            try (InputStream input = new BufferedInputStream(connection.getInputStream());
                 OutputStream output = resolver.openOutputStream(uri)) {
                if (output == null) throw new IllegalStateException("Android não abriu o arquivo do vídeo");
                byte[] buffer = new byte[128 * 1024];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                output.flush();
            }
            ContentValues ready = new ContentValues();
            ready.put(MediaStore.Video.Media.IS_PENDING, 0);
            resolver.update(uri, ready, null, null);
            return uri;
        } catch (Exception error) {
            resolver.delete(uri, null, null);
            throw error;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private String readText(String urlString) throws Exception {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(urlString).openConnection();
            connection.setConnectTimeout(15_000);
            connection.setReadTimeout(20_000);
            connection.setRequestProperty("User-Agent", "CarlosKwaiBridge/1.0");
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new IllegalStateException("HTTP " + status);
            StringBuilder builder = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                    connection.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) builder.append(line).append('\n');
            }
            return builder.toString();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void launchKwaiShare(Uri videoUri, String caption) {
        try {
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("video/mp4");
            send.putExtra(Intent.EXTRA_STREAM, videoUri);
            if (!caption.isEmpty()) send.putExtra(Intent.EXTRA_TEXT, caption);
            send.setClipData(ClipData.newUri(getContentResolver(), "Kwai video", videoUri));
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            send.setPackage("com.kwai.video");
            if (send.resolveActivity(getPackageManager()) == null) {
                setStatus("O Kwai instalado não aceitou o compartilhamento direto. Abra o app Carlos Kwai Bridge para diagnóstico.");
                prefs().edit().putString("stage", "share_intent_unsupported").apply();
                return;
            }
            startActivity(send);
            prefs().edit().putString("stage", "kwai_opened").apply();
        } catch (Throwable error) {
            setStatus("Não consegui abrir o Kwai: " + safeMessage(error));
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) return;
        if (!"com.kwai.video".contentEquals(event.getPackageName())) return;
        if (prefs().getString("pending_run", "").isEmpty()) return;
        if (System.currentTimeMillis() - lastUiActionAt < UI_COOLDOWN_MS) return;
        if (!uiScheduled.compareAndSet(false, true)) return;
        mainHandler.postDelayed(() -> {
            try {
                driveKwaiUi();
            } finally {
                uiScheduled.set(false);
            }
        }, 900L);
    }

    private void driveKwaiUi() {
        String pendingRun = prefs().getString("pending_run", "");
        if (pendingRun.isEmpty()) return;

        long started = prefs().getLong("pending_started_at", 0L);
        if (started > 0 && System.currentTimeMillis() - started > 8 * 60_000L) {
            setStatus("O Kwai não concluiu a tela de publicação em 8 minutos. Mantive o pacote pendente para revisão.");
            return;
        }

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;
        try {
            String caption = prefs().getString("pending_caption", "");
            List<AccessibilityNodeInfo> editables = new ArrayList<>();
            collectEditableNodes(root, editables);
            boolean captionSet = false;
            if (!caption.isEmpty() && !editables.isEmpty()) {
                AccessibilityNodeInfo target = editables.get(editables.size() - 1);
                android.os.Bundle args = new android.os.Bundle();
                args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, caption);
                captionSet = target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT);
                if (captionSet) prefs().edit().putString("stage", "caption_set").apply();
            }
            for (AccessibilityNodeInfo editable : editables) editable.recycle();

            AccessibilityNodeInfo publish = findByLabels(root, PUBLISH_LABELS);
            String stage = prefs().getString("stage", "");
            if (publish != null && (captionSet || "caption_set".equals(stage) || !editables.isEmpty())) {
                if (clickNode(publish)) {
                    lastUiActionAt = System.currentTimeMillis();
                    setStatus("Publicação enviada ao Kwai. Confirmando pacote " + pendingRun + ".");
                    prefs().edit().putInt("confirm_attempts", 0).apply();
                    mainHandler.postDelayed(this::confirmPublishCompletion, 5000L);
                    return;
                }
            }

            int existingClicks = prefs().getInt("ui_click_count", 0);
            if (existingClicks >= 6) {
                setStatus("O fluxo do Kwai mudou. Parei antes de clicar em algo incerto.");
                return;
            }
            AccessibilityNodeInfo next = findByLabels(root, NEXT_LABELS);
            if (next != null && clickNode(next)) {
                lastUiActionAt = System.currentTimeMillis();
                int clicks = existingClicks + 1;
                prefs().edit().putInt("ui_click_count", clicks).putString("stage", "advancing").apply();
                setStatus("Avançando na publicação do Kwai (etapa " + clicks + ").");
            }
        } finally {
            root.recycle();
        }
    }

    private void confirmPublishCompletion() {
        SharedPreferences p = prefs();
        String run = p.getString("pending_run", "");
        if (run.isEmpty()) return;
        AccessibilityNodeInfo root = getRootInActiveWindow();
        boolean composerStillVisible = false;
        if (root != null) {
            try {
                AccessibilityNodeInfo publish = findByLabels(root, PUBLISH_LABELS);
                if (publish != null) {
                    composerStillVisible = true;
                    publish.recycle();
                }
            } finally {
                root.recycle();
            }
        }
        if (composerStillVisible) {
            int attempts = p.getInt("confirm_attempts", 0) + 1;
            p.edit().putInt("confirm_attempts", attempts).apply();
            if (attempts < 3) {
                setStatus("O Kwai ainda está processando a publicação. Conferindo novamente.");
                mainHandler.postDelayed(this::confirmPublishCompletion, 5000L);
            } else {
                setStatus("A tela de publicação continuou aberta. Mantive o pacote pendente em vez de marcar como publicado.");
            }
            return;
        }
        markPendingAsCompleted();
    }

    private void markPendingAsCompleted() {
        SharedPreferences p = prefs();
        String run = p.getString("pending_run", "");
        if (run.isEmpty()) return;
        String oldUri = p.getString("previous_uri", "");
        SharedPreferences.Editor editor = p.edit();
        editor.putString("last_run", run);
        editor.putString("previous_uri", p.getString("pending_uri", ""));
        editor.remove("pending_run");
        editor.remove("pending_caption");
        editor.remove("pending_uri");
        editor.remove("pending_started_at");
        editor.putString("stage", "complete");
        editor.putInt("ui_click_count", 0);
        editor.remove("confirm_attempts");
        editor.apply();
        setStatus("Pacote " + run + " concluído. Aguardando o próximo.");
        deleteOldMedia(oldUri);
    }

    private void deleteOldMedia(String uriString) {
        if (uriString == null || uriString.isEmpty()) return;
        try {
            getContentResolver().delete(Uri.parse(uriString), null, null);
        } catch (Throwable ignored) {
        }
    }

    private void collectEditableNodes(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> output) {
        if (node == null) return;
        if (node.isEditable() || "android.widget.EditText".contentEquals(node.getClassName())) {
            output.add(AccessibilityNodeInfo.obtain(node));
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                collectEditableNodes(child, output);
                child.recycle();
            }
        }
    }

    private AccessibilityNodeInfo findByLabels(AccessibilityNodeInfo root, List<String> labels) {
        if (root == null) return null;
        String text = normalize(root.getText());
        String description = normalize(root.getContentDescription());
        for (String label : labels) {
            String normalizedLabel = normalize(label);
            if (text.equals(normalizedLabel) || description.equals(normalizedLabel)) {
                return AccessibilityNodeInfo.obtain(root);
            }
        }
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child = root.getChild(i);
            if (child != null) {
                AccessibilityNodeInfo found = findByLabels(child, labels);
                child.recycle();
                if (found != null) return found;
            }
        }
        return null;
    }

    private boolean clickNode(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo current = node;
        for (int depth = 0; depth < 4 && current != null; depth++) {
            if (current.isClickable() && current.isEnabled()) {
                boolean clicked = current.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                if (depth > 0) current.recycle();
                node.recycle();
                return clicked;
            }
            AccessibilityNodeInfo parent = current.getParent();
            if (depth > 0) current.recycle();
            current = parent;
        }
        if (current != null && current != node) current.recycle();
        node.recycle();
        return false;
    }

    private String normalize(CharSequence value) {
        if (value == null) return "";
        return value.toString().trim().toLowerCase(Locale.ROOT);
    }

    private String safeMessage(Throwable error) {
        String message = error.getMessage();
        return message == null || message.trim().isEmpty() ? error.getClass().getSimpleName() : message;
    }

    @Override
    public void onInterrupt() {
        setStatus("Acessibilidade do Kwai foi interrompida pelo Android.");
    }

    @Override
    public void onDestroy() {
        stopped = true;
        if (pollThread != null) pollThread.interrupt();
        if (instance == this) instance = null;
        super.onDestroy();
    }
}
