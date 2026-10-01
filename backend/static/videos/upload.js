/**
 * Admin'da video yuklash: fayl brauzerdan to'g'ridan-to'g'ri storage'ga ketadi.
 *
 * Tartib: backend multipart sessiyani boshlaydi → har qism uchun imzolangan URL beradi →
 * brauzer qismlarni PUT qiladi → backend qismlarni birlashtiradi va ffmpeg vazifasini qo'yadi.
 */
(function () {
  "use strict";

  // Imzolar muddati o'tib ketmasligi uchun URL'lar to'plam-to'plam so'raladi.
  var BATCH = 10;
  var POLL_MS = 5000;

  function csrf() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function api(url, options) {
    var init = options || {};
    init.headers = Object.assign({ "X-CSRFToken": csrf() }, init.headers || {});
    init.credentials = "same-origin";
    return fetch(url, init).then(function (response) {
      if (!response.ok) {
        return response
          .json()
          .catch(function () {
            return null;
          })
          .then(function (body) {
            var detail = body && body.error ? body.error.message : "";
            throw new Error(detail || "Server xatosi: " + response.status);
          });
      }
      return response.status === 204 ? null : response.json();
    });
  }

  function json(url, payload) {
    return api(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  /** Bitta qismni yuboradi va ETag qaytaradi. XHR ishlatiladi: progress kerak. */
  function putPart(url, blob, onProgress) {
    return new Promise(function (resolve, reject) {
      var request = new XMLHttpRequest();
      request.open("PUT", url, true);
      request.upload.onprogress = function (event) {
        if (event.lengthComputable) onProgress(event.loaded);
      };
      request.onload = function () {
        if (request.status < 200 || request.status >= 300) {
          reject(new Error("Qism yuborilmadi: " + request.status));
          return;
        }
        var etag = request.getResponseHeader("ETag");
        if (!etag) {
          reject(new Error("Storage ETag qaytarmadi (CORS sozlamasini tekshiring)."));
          return;
        }
        resolve(etag);
      };
      request.onerror = function () {
        reject(new Error("Tarmoq xatosi."));
      };
      request.ontimeout = function () {
        reject(new Error("Vaqt tugadi."));
      };
      request.send(blob);
    });
  }

  function setup(root) {
    var input = root.querySelector("[data-video-input]");
    var file = root.querySelector("[data-video-file]");
    var progress = root.querySelector("[data-video-progress]");
    var bar = root.querySelector("[data-video-bar]");
    var message = root.querySelector("[data-video-message]");
    var cancel = root.querySelector("[data-video-cancel]");
    var startUrl = root.dataset.startUrl;
    var maxMb = parseInt(root.dataset.maxMb, 10) || 2048;
    var active = null;

    function say(text) {
      message.textContent = text;
    }

    function show(percent) {
      bar.style.width = Math.min(100, Math.round(percent)) + "%";
    }

    function reset() {
      progress.hidden = true;
      show(0);
      active = null;
      file.value = "";
    }

    function watch(id) {
      var url = startUrl + id + "/";
      var timer = window.setInterval(function () {
        api(url, { method: "GET" })
          .then(function (video) {
            if (video.status === "PROCESSING") {
              say("Qayta ishlanmoqda…");
              return;
            }
            window.clearInterval(timer);
            if (video.status === "READY") {
              say("Video tayyor. Saqlashni bosing.");
              show(100);
            } else {
              say("Xato: " + (video.error || "noma'lum"));
            }
          })
          .catch(function () {
            window.clearInterval(timer);
          });
      }, POLL_MS);
    }

    async function upload(chosen) {
      if (chosen.size > maxMb * 1024 * 1024) {
        say("Fayl juda katta. Ruxsat: " + maxMb + " MB.");
        return;
      }
      progress.hidden = false;
      say("Yuklash boshlandi…");

      var started;
      try {
        started = await json(startUrl, {
          filename: chosen.name,
          size: chosen.size,
          content_type: chosen.type,
        });
      } catch (error) {
        say(error.message);
        return;
      }

      var id = started.video.id;
      var partSize = started.part_size;
      var total = started.part_count;
      active = { id: id, cancelled: false };
      var done = [];
      var sentBytes = 0;

      try {
        for (var first = 1; first <= total; first += BATCH) {
          var numbers = [];
          for (var n = first; n < first + BATCH && n <= total; n += 1) numbers.push(n);
          var signed = await json(startUrl + id + "/parts/", { part_numbers: numbers });

          for (var i = 0; i < signed.length; i += 1) {
            if (active.cancelled) throw new Error("Bekor qilindi.");
            var number = signed[i].part_number;
            var blob = chosen.slice((number - 1) * partSize, number * partSize);
            var base = sentBytes;
            var etag = await putPart(signed[i].url, blob, function (loaded) {
              show(((base + loaded) / chosen.size) * 100);
            });
            sentBytes += blob.size;
            done.push({ part_number: number, etag: etag.replace(/"/g, "") });
            say("Yuborildi: " + done.length + " / " + total);
          }
        }

        say("Birlashtirilmoqda…");
        await json(startUrl + id + "/complete/", { parts: done });
        input.value = id;
        say("Qayta ishlanmoqda…");
        watch(id);
        active = null;
      } catch (error) {
        say(error.message);
        try {
          await json(startUrl + id + "/abort/", {});
        } catch (ignored) {
          // Sessiya allaqachon yopilgan bo'lishi mumkin.
        }
        reset();
      }
    }

    file.addEventListener("change", function () {
      if (file.files && file.files[0]) upload(file.files[0]);
    });

    cancel.addEventListener("click", function () {
      if (active) active.cancelled = true;
      say("Bekor qilinmoqda…");
    });

    // Yuklash davom etayotganda sahifadan chiqib ketishdan ogohlantiradi.
    window.addEventListener("beforeunload", function (event) {
      if (active) {
        event.preventDefault();
        event.returnValue = "";
      }
    });

    var status = root.querySelector("[data-video-status]");
    if (status && status.dataset.status === "PROCESSING") {
      progress.hidden = false;
      watch(status.dataset.id);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-video-upload]").forEach(setup);
  });
})();
