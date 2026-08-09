/**
 * scripts/send_notifications.js
 * يعمل عبر GitHub Actions (سير عمل send-notifications.yml) كل بضع دقائق.
 * يستخدم مفتاح Service Account لإرسال إشعارات FCM مباشرة — بدون أي سيرفر
 * أو Cloud Functions.
 *
 * يرسل 3 أنواع من الإشعارات، ويعلّم كل حجز أُرسل له حتى لا يتكرر الإرسال:
 * 1) تأكيد حجز جديد   → createdNotifySent
 * 2) إلغاء حجز        → cancelNotifySent
 * 3) تذكير قبل يوم     → reminderSent
 */

const admin = require('firebase-admin');
const fs = require('fs');

const serviceAccount = JSON.parse(fs.readFileSync('./service-account.json', 'utf-8'));
admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });

const db = admin.firestore();
const messaging = admin.messaging();

async function sendOne(fcmToken, title, body, link){
  try {
    await messaging.send({
      token: fcmToken,
      notification: { title, body: body || '' },
      data: { link: link || '' },
      android: { priority: 'high' }
    });
    return true;
  } catch (err) {
    console.error('تعذر إرسال إشعار:', err.message || err);
    return false;
  }
}

async function run(){
  const snap = await db.collectionGroup('bookings').get();
  const now = Date.now();
  const windowStart = now + 23 * 60 * 60 * 1000;
  const windowEnd = now + 25 * 60 * 60 * 1000;

  let sentCount = 0;

  for (const doc of snap.docs) {
    const bk = doc.data();
    if (!bk.fcmToken) continue;
    const bizId = doc.ref.parent.parent.id;
    const link = '#/ticket/' + bizId + '/' + doc.id + '/' + (bk.cancelToken || '');

    // 1) تأكيد حجز جديد
    if (bk.status === 'confirmed' && !bk.createdNotifySent) {
      const ok = await sendOne(bk.fcmToken, 'تم تأكيد حجزك', bk.visitorName ? `مرحباً ${bk.visitorName}، تم تأكيد حجزك بنجاح.` : 'تم تأكيد حجزك بنجاح.', link);
      if (ok) { await doc.ref.update({ createdNotifySent: true }); sentCount++; }
    }

    // 2) إلغاء الحجز
    if (bk.status === 'cancelled' && !bk.cancelNotifySent) {
      const ok = await sendOne(bk.fcmToken, 'تم إلغاء الحجز', 'تم إلغاء حجزك بنجاح.', '');
      if (ok) { await doc.ref.update({ cancelNotifySent: true }); sentCount++; }
    }

    // 3) تذكير قبل الموعد بيوم (فقط للحجوزات ذات تاريخ ووقت ثابتين، بتوقيت اليابان)
    if (bk.status === 'confirmed' && !bk.reminderSent && bk.date && bk.time) {
      const apptTime = new Date(`${bk.date}T${bk.time}:00+09:00`).getTime();
      if (!Number.isNaN(apptTime) && apptTime >= windowStart && apptTime <= windowEnd) {
        const ok = await sendOne(bk.fcmToken, 'تذكير: لديك موعد غداً', `موعدك غداً الساعة ${bk.time}`, link);
        if (ok) { await doc.ref.update({ reminderSent: true }); sentCount++; }
      }
    }
  }

  console.log(`تم إرسال ${sentCount} إشعار.`);
}

run().catch(err => {
  console.error('فشل تشغيل السكربت:', err);
  process.exit(1);
});
