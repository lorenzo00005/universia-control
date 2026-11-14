/*
 * Universia Control - script para la landing.
 * 1) Al cargar, manda a tu CRM los datos del clic del anuncio (fbclid, _fbc, _fbp, utm_*) y recibe un código corto.
 * 2) Los botones con data-wa-number abren WhatsApp con el mensaje + ese código ([K7X2QM]).
 *    El CRM lo lee en el primer mensaje y une el chat con el clic.
 *
 * Uso (pegar antes de </body>, después del Pixel de Meta):
 *   <script src="tracker.js" data-crm="https://crm.tudominio.com"></script>
 *   <a href="#" data-wa-number="5491100000000" data-wa-text="Hola, quiero información">Escribinos</a>
 */
(function () {
  var script = document.currentScript;
  var crm = ((script && script.getAttribute("data-crm")) || "").replace(/\/$/, "");
  if (!crm) { console.warn("[tracker] falta data-crm"); return; }

  var params = new URLSearchParams(location.search);
  function cookie(name) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : null;
  }

  var code = null;
  var ready = null;
  try { code = sessionStorage.getItem("ctw_code"); } catch (e) {}

  function register() {
    // El Pixel crea _fbc/_fbp de forma asíncrona: se espera un instante antes de leerlas.
    return new Promise(function (resolve) { setTimeout(resolve, 600); }).then(function () {
      return fetch(crm + "/track/click", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fbclid: params.get("fbclid"),
          fbc: cookie("_fbc"),
          fbp: cookie("_fbp"),
          source_url: location.href.split("#")[0],
          utm_source: params.get("utm_source"),
          utm_medium: params.get("utm_medium"),
          utm_campaign: params.get("utm_campaign"),
          utm_content: params.get("utm_content"),
        }),
        keepalive: true,
      });
    }).then(function (r) { return r.json(); }).then(function (data) {
      code = data.code;
      try { sessionStorage.setItem("ctw_code", code); } catch (e) {}
      return code;
    }).catch(function () { return null; }); // si el CRM no responde, el botón igual abre WhatsApp
  }

  ready = code ? Promise.resolve(code) : register();

  function waUrl(el) {
    var number = (el.getAttribute("data-wa-number") || "").replace(/\D/g, "");
    var text = el.getAttribute("data-wa-text") || "Hola";
    if (code) text += " [" + code + "]";
    return "https://wa.me/" + number + "?text=" + encodeURIComponent(text);
  }

  document.addEventListener("click", function (ev) {
    var el = ev.target.closest ? ev.target.closest("[data-wa-number]") : null;
    if (!el) return;
    ev.preventDefault();
    if (window.fbq) { try { window.fbq("track", "Contact"); } catch (e) {} }
    // Si el código todavía no llegó, se espera hasta 1,5 s antes de abrir.
    Promise.race([ready, new Promise(function (r) { setTimeout(r, 1500); })]).then(function () {
      location.href = waUrl(el);
    });
  });
})();
