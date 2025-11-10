// utils/security.js
/*
Anti-cheat script for EchoViva 2.0
----------------------------------
- Warns if the user tries to switch tabs or leave the window.
- Can be extended to trigger backend logging via Streamlit events.
- Lightweight and non-blocking.
*/

(function () {
  console.log("SECURITY loaded!")
  // Prevent multiple injections
  if (window.__ECHO_VIVA_SECURITY_LOADED__) return;
  window.__ECHO_VIVA_SECURITY_LOADED__ = true;

  let warningShown = false;
  let tabSwitchCount = 0;
  let cheatAlert = null;

  function showWarning(message) {
    // Create or reuse a warning div
    if (!cheatAlert) {
      cheatAlert = document.createElement("div");
      cheatAlert.style.position = "fixed";
      cheatAlert.style.top = "10px";
      cheatAlert.style.right = "10px";
      cheatAlert.style.background =
        "linear-gradient(135deg, rgba(255, 0, 0, 0.8), rgba(255, 100, 100, 0.8))";
      cheatAlert.style.color = "white";
      cheatAlert.style.padding = "12px 16px";
      cheatAlert.style.fontSize = "14px";
      cheatAlert.style.borderRadius = "8px";
      cheatAlert.style.zIndex = "999999";
      cheatAlert.style.boxShadow = "0 0 12px rgba(0,0,0,0.5)";
      cheatAlert.style.fontFamily = "Poppins, sans-serif";
      cheatAlert.style.transition = "opacity 0.4s ease";
      cheatAlert.textContent = message;
      document.body.appendChild(cheatAlert);
    } else {
      cheatAlert.textContent = message;
      cheatAlert.style.opacity = "1";
    }

    setTimeout(() => {
      if (cheatAlert) cheatAlert.style.opacity = "0";
    }, 4000);
  }

  // Listen for tab visibility changes
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      tabSwitchCount++;
      warningShown = true;
      showWarning("⚠️ Tab switch detected! Please stay on this tab during the viva.");
    }
  });

  // Detect window blur (switching apps)
  window.addEventListener("blur", () => {
    console.log("Window lost focus");
    tabSwitchCount++;
    warningShown = true;
    showWarning("🚫 Focus lost! Please remain in the viva window.");
  });

  // Detect DevTools open (basic heuristic)
  let devtoolsOpen = false;
  const threshold = 160;
  setInterval(() => {
    const widthDiff = window.outerWidth - window.innerWidth > threshold;
    const heightDiff = window.outerHeight - window.innerHeight > threshold;
    if (widthDiff || heightDiff) {
      if (!devtoolsOpen) {
        devtoolsOpen = true;
        showWarning("⚠️ Developer tools detected! Please close them to continue viva.");
      }
    } else {
      devtoolsOpen = false;
    }
  }, 1000);

  // Optionally notify Streamlit backend if needed (future enhancement)
  window.getEchoVivaCheatCount = () => tabSwitchCount;
})();
