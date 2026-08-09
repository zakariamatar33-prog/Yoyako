/**
 * native-bridge.js
 * يُجمَّع (bundle) هذا الملف عبر esbuild في سير عمل GitHub Actions إلى
 * www/native-bridge.bundled.js — لأن Capacitor 3+ لا يدعم استخدام الإضافات
 * (Plugins) عبر وسم <script> مباشرة، ويتطلب حزمة (bundler) لأي كود يستخدم
 * import. index.html يحمّل الملف المُجمَّع فقط عبر <script> عادي، ويستخدم
 * الدوال المتاحة على window.YoyakoNative — لا حاجة لأي تعديل إضافي هناك.
 *
 * عند تشغيل الموقع كمتصفح عادي (وليس داخل تطبيق أندرويد)، Capacitor.isNativePlatform()
 * ترجع false تلقائياً، وكل الدوال هنا تصبح بلا تأثير (no-op) بأمان.
 */
import { Capacitor } from '@capacitor/core';
import { PushNotifications } from '@capacitor/push-notifications';
import { SplashScreen } from '@capacitor/splash-screen';
import { Network } from '@capacitor/network';
import { App } from '@capacitor/app';
import { AdMob, BannerAdPosition, BannerAdSize } from '@capacitor-community/admob';

const isNative = Capacitor.isNativePlatform();

async function initPushNotifications(onTokenReady) {
  if (!isNative) return;
  try {
    const perm = await PushNotifications.requestPermissions();
    if (perm.receive !== 'granted') return;
    await PushNotifications.register();

    PushNotifications.addListener('registration', (token) => {
      if (onTokenReady) onTokenReady(token.value);
    });
    PushNotifications.addListener('registrationError', (err) => {
      console.error('FCM registration error:', err);
    });
    // الضغط على الإشعار (سواء كان التطبيق مفتوحاً، بالخلفية، أو مغلقاً تماماً)
    PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      const data = (action.notification && action.notification.data) || {};
      if (data.link) {
        const hashPart = data.link.indexOf('#') > -1 ? data.link.split('#')[1] : data.link;
        location.hash = '#' + hashPart.replace(/^#/, '');
      }
    });
  } catch (err) {
    console.error('initPushNotifications error:', err);
  }
}

async function hideSplash() {
  if (!isNative) return;
  try { await SplashScreen.hide(); } catch (e) {}
}

function onNetworkChange(cb) {
  if (!isNative) {
    window.addEventListener('online', () => cb(true));
    window.addEventListener('offline', () => cb(false));
    cb(navigator.onLine);
    return;
  }
  Network.getStatus().then((s) => cb(s.connected));
  Network.addListener('networkStatusChange', (s) => cb(s.connected));
}

async function initAdMob() {
  if (!isNative) return;
  try {
    await AdMob.initialize({ initializeForTesting: true });
  } catch (err) {
    console.error('initAdMob error:', err);
  }
}

/**
 * adUnitId: مرّري معرّف إعلان حقيقي من حساب AdMob الخاص بك بعد الموافقة عليه،
 * أو اتركيها فارغة لاستخدام معرّف Google التجريبي الرسمي (آمن دائماً للتطوير).
 */
async function showBannerAd(adUnitId) {
  if (!isNative) return;
  const TEST_BANNER_ID = 'ca-app-pub-3940256099942544/6300978111';
  try {
    await AdMob.showBanner({
      adId: adUnitId || TEST_BANNER_ID,
      adSize: BannerAdSize.ADAPTIVE_BANNER,
      position: BannerAdPosition.BOTTOM_CENTER,
      isTesting: !adUnitId
    });
  } catch (err) {
    console.error('showBannerAd error:', err);
  }
}

function handleAppUrlOpen(cb) {
  if (!isNative) return;
  App.addListener('appUrlOpen', (data) => {
    if (data && data.url) cb(data.url);
  });
}

window.YoyakoNative = {
  isNative,
  initPushNotifications,
  hideSplash,
  onNetworkChange,
  initAdMob,
  showBannerAd,
  handleAppUrlOpen
};
