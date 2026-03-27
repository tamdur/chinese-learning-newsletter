/* Shared JS for all 今日讀報 page types.
   This is a reference artifact — assemble.py reads and injects it.
   Expects: const GLOSSARY = {...}; defined before this script. */

(function () {
  'use strict';

  var lookupMode = false;

  // === Translation toggles ===

  document.querySelectorAll('.translation-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const container = btn.closest('.article') || btn.closest('.wisdom-section') || btn.closest('.obsession-section') || btn.parentElement;
      const enDiv = container.querySelector('.article-body-en') || container.querySelector('.section-body-en');
      if (!enDiv) return;
      const isHidden = enDiv.hidden;
      enDiv.hidden = !isHidden;
      btn.textContent = isHidden
        ? '隱藏翻譯 Hide Translation'
        : '顯示翻譯 Show Translation';
    });
  });

  // === Mobile character lookup ===

  var isMobile = window.matchMedia('(pointer: coarse)').matches;

  if (isMobile) {
    var longPressTimer = null;
    var feedbackTimer = null;
    var startX = 0;
    var startY = 0;
    var activeSpan = null;
    var LONG_PRESS_MS = 400;
    var MOVE_THRESHOLD = 10;

    var popup = document.getElementById('char-popup');
    var popupChar = document.getElementById('popup-char');
    var popupZhuyin = document.getElementById('popup-zhuyin');
    var popupDef = document.getElementById('popup-def');
    var lookupToggleBtn = document.getElementById('lookup-toggle');

    function positionPopup(targetSpan) {
      var rect = targetSpan.getBoundingClientRect();
      var popupWidth = 280;
      var margin = 8;
      var gap = 6;
      var vw = window.innerWidth;

      popup.classList.add('visible');
      var popupHeight = popup.offsetHeight;

      var left = rect.left + rect.width / 2 - popupWidth / 2;
      left = Math.max(margin, Math.min(left, vw - popupWidth - margin));

      var top = rect.top - popupHeight - gap;
      if (top < margin) {
        top = rect.bottom + gap;
      }

      popup.style.left = left + 'px';
      popup.style.top = top + 'px';
    }

    function findLongestMatch(targetSpan) {
      if (typeof GLOSSARY === 'undefined') return null;

      var parent = targetSpan.closest('p, h2, li') || targetSpan.parentElement;
      var spans = [].slice.call(parent.querySelectorAll('.c'));
      var targetIdx = spans.indexOf(targetSpan);
      if (targetIdx === -1) return null;

      var chars = spans.map(function (s) { return s.textContent; });
      var MAX_WORD_LEN = 6;
      var bestMatch = null;
      var bestSpans = null;

      for (var len = Math.min(MAX_WORD_LEN, chars.length); len >= 1; len--) {
        var startMin = Math.max(0, targetIdx - len + 1);
        var startMax = Math.min(targetIdx, chars.length - len);

        for (var start = startMin; start <= startMax; start++) {
          var candidate = chars.slice(start, start + len).join('');
          if (GLOSSARY[candidate]) {
            if (!bestMatch || candidate.length > bestMatch.length) {
              bestMatch = candidate;
              bestSpans = spans.slice(start, start + len);
            }
          }
        }

        if (bestMatch && bestMatch.length === len) break;
      }

      return bestMatch
        ? { text: bestMatch, entry: GLOSSARY[bestMatch], spans: bestSpans }
        : null;
    }

    function showPopup(char, targetSpan) {
      var match = findLongestMatch(targetSpan);

      if (match) {
        popupChar.textContent = match.text;
        popupZhuyin.textContent = match.entry.zhuyin;
        popupDef.textContent = match.entry.english;
      } else {
        popupChar.textContent = char;
        popupZhuyin.textContent = '';
        popupDef.textContent = '(not in glossary)';
      }

      document.querySelectorAll('.c.touch-selected').forEach(function (el) {
        el.classList.remove('touch-selected');
      });

      var highlightSpans = match ? match.spans : [targetSpan];
      highlightSpans.forEach(function (s) { s.classList.add('touch-selected'); });
      activeSpan = targetSpan;

      positionPopup(targetSpan);
    }

    function hidePopup() {
      popup.classList.remove('visible');
      document.querySelectorAll('.c.touch-selected').forEach(function (el) {
        el.classList.remove('touch-selected');
      });
      activeSpan = null;
    }

    document.getElementById('popup-close').addEventListener('click', hidePopup);

    document.addEventListener('click', function (e) {
      if (!popup.classList.contains('visible')) return;
      if (popup.contains(e.target)) return;
      if (!e.target.closest('.c')) {
        hidePopup();
      }
    });

    var scrollDismissAttached = false;
    function attachScrollDismiss() {
      if (scrollDismissAttached) return;
      scrollDismissAttached = true;
      window.addEventListener('scroll', function onScroll() {
        hidePopup();
        window.removeEventListener('scroll', onScroll);
        scrollDismissAttached = false;
      }, { once: true });
    }

    document.addEventListener('touchstart', function (e) {
      var span = e.target.closest('.c');
      if (!span) return;

      var touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;

      feedbackTimer = setTimeout(function () {
        span.classList.add('touch-active');
      }, 100);

      longPressTimer = setTimeout(function () {
        span.classList.remove('touch-active');
        showPopup(span.textContent, span);
        attachScrollDismiss();
      }, LONG_PRESS_MS);
    }, { passive: true });

    document.addEventListener('touchmove', function (e) {
      if (!longPressTimer) return;
      var touch = e.touches[0];
      if (Math.abs(touch.clientX - startX) > MOVE_THRESHOLD ||
          Math.abs(touch.clientY - startY) > MOVE_THRESHOLD) {
        clearTimeout(longPressTimer);
        clearTimeout(feedbackTimer);
        longPressTimer = null;
        document.querySelectorAll('.touch-active').forEach(function (el) {
          el.classList.remove('touch-active');
        });
      }
    }, { passive: true });

    document.addEventListener('touchend', function (e) {
      clearTimeout(longPressTimer);
      clearTimeout(feedbackTimer);
      longPressTimer = null;
      var span = e.target.closest('.c');
      if (span) span.classList.remove('touch-active');
    }, { passive: true });

    document.addEventListener('touchcancel', function () {
      clearTimeout(longPressTimer);
      clearTimeout(feedbackTimer);
      longPressTimer = null;
      document.querySelectorAll('.touch-active').forEach(function (el) {
        el.classList.remove('touch-active');
      });
    }, { passive: true });

    lookupToggleBtn.addEventListener('click', function () {
      lookupMode = !lookupMode;
      this.textContent = lookupMode ? '查詢模式 ON' : '查詢模式 OFF';
      this.classList.toggle('active', lookupMode);
    });

    document.addEventListener('click', function (e) {
      if (!lookupMode) return;
      var span = e.target.closest('.c');
      if (!span) return;
      e.stopPropagation();
      showPopup(span.textContent, span);
      attachScrollDismiss();
    });
  }
})();
