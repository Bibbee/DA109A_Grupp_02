document.addEventListener("DOMContentLoaded", () => {
  const slides = document.querySelectorAll(".slide");
  const dots = document.querySelectorAll(".dot");

  // Count-up animation (runs once per slide)
  function animateCount(el) {
    const target = Number(el.dataset.to || "0");
    if (el.dataset.done === "1") return;   // run once
    el.dataset.done = "1";

    const duration = 900;
    const start = performance.now();

    function tick(now) {
      const p = Math.min((now - start) / duration, 1);
      const value = Math.floor(target * p);
      el.textContent = value;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = target;
    }
    requestAnimationFrame(tick);
  }

  // Mark slide active + run its animations
  function activateSlide(slide) {
    slides.forEach(s => s.classList.remove("is-active"));
    slide.classList.add("is-active");

    // update dots
    const idx = Number(slide.dataset.slide) - 1;
    dots.forEach(d => d.classList.remove("active"));
    if (dots[idx]) dots[idx].classList.add("active");

    // run count-ups in this slide only
    slide.querySelectorAll(".count-up").forEach(animateCount);
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        activateSlide(entry.target);
      }
    });
  }, { threshold: 0.6 });

  slides.forEach(slide => observer.observe(slide));

  // activate first slide immediately
  if (slides[0]) activateSlide(slides[0]);
});
