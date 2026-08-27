#!/usr/bin/env bash
set -euo pipefail

: "${GENYMOTION_API_TOKEN:?GENYMOTION_API_TOKEN ausente}"
: "${GENYMOTION_INSTANCE_UUID:?GENYMOTION_INSTANCE_UUID ausente}"

ANDROID_SDK_PATH="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$ANDROID_SDK_PATH" ]]; then
  echo "ANDROID_SDK_ROOT/ANDROID_HOME não definido"
  exit 1
fi

python -m pip install --disable-pip-version-check --quiet 'gmsaas>=1.16.0'
gmsaas auth token "$GENYMOTION_API_TOKEN"
gmsaas config set android-sdk-path "$ANDROID_SDK_PATH"

echo "Conectando ao Android virtual $GENYMOTION_INSTANCE_UUID..."
gmsaas instances adbconnect "$GENYMOTION_INSTANCE_UUID"
adb wait-for-device
adb devices

APK_PATH="${1:-kwai-android/app/build/outputs/apk/debug/app-debug.apk}"
if [[ ! -f "$APK_PATH" ]]; then
  echo "APK não encontrado: $APK_PATH"
  exit 1
fi

echo "Instalando/atualizando Carlos Kwai Bridge..."
adb install -r "$APK_PATH"

PACKAGE='com.carlos.kwaibridge'
SERVICE='com.carlos.kwaibridge/com.carlos.kwaibridge.KwaiAccessibilityService'

# Ativa a acessibilidade pelo shell do Android virtual, eliminando o toque manual.
current="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
if [[ -z "$current" || "$current" == 'null' ]]; then
  merged="$SERVICE"
elif [[ ":$current:" == *":$SERVICE:"* ]]; then
  merged="$current"
else
  merged="$current:$SERVICE"
fi
adb shell settings put secure enabled_accessibility_services "$merged"
adb shell settings put secure accessibility_enabled 1

# O APK de debug permite inicializar a preferência de publicação automática sem UI.
adb shell am force-stop "$PACKAGE" || true
cat > /tmp/kwai_bridge.xml <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="enabled" value="true" />
    <string name="last_status">Android na nuvem configurado. Publicação automática ativa.</string>
</map>
XML
adb shell "run-as $PACKAGE mkdir -p shared_prefs" || true
cat /tmp/kwai_bridge.xml | adb shell "run-as $PACKAGE sh -c 'cat > shared_prefs/kwai_bridge.xml'" || true

# Evita suspensão agressiva e mantém o Android virtual pronto para receber a fila.
adb shell dumpsys deviceidle whitelist +"$PACKAGE" || true
adb shell settings put global stay_on_while_plugged_in 7 || true
adb shell svc power stayon true || true
adb shell input keyevent KEYCODE_WAKEUP || true
adb shell wm dismiss-keyguard || true

# Inicia o bridge.
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 2

if adb shell pm path com.kwai.video >/dev/null 2>&1; then
  echo "KWAI_INSTALLED=true"
  adb shell monkey -p com.kwai.video -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
else
  echo "KWAI_INSTALLED=false"
  echo "O app oficial do Kwai ainda precisa ser instalado e logado uma única vez no Android virtual."
fi

echo "Accessibility services: $(adb shell settings get secure enabled_accessibility_services | tr -d '\r')"
echo "Bootstrap concluído."
