importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyAbS_WXbOEuIQYJe5ZsLLTwj38XRaMWVMY",
  authDomain: "collector-app-b5469.firebaseapp.com",
  projectId: "collector-app-b5469",
  messagingSenderId: "219228786482",
  appId: "1:219228786482:web:1fdaaac26440cf4c39d12b"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  self.registration.showNotification(payload.notification.title, {
    body: payload.notification.body,
  });
});