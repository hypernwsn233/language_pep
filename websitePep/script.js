const scene = document.getElementById("scene");

if (scene) {
  window.addEventListener("pointermove", (ev) => {
    const x = ev.clientX / window.innerWidth - 0.5;
    const y = ev.clientY / window.innerHeight - 0.5;

    scene.style.transform = `rotateX(${y * -10}deg) rotateY(${x * 14}deg)`;
  });

  window.addEventListener("pointerleave", () => {
    scene.style.transform = "rotateX(0deg) rotateY(0deg)";
  });
}

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  {
    threshold: 0.12,
  }
);

document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
