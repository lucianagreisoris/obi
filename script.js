const yearNode = document.querySelector("#year");
const mediaButtons = document.querySelectorAll("[data-modal-target]");
const closeButtons = document.querySelectorAll(".modal-close");
const modalSlideshows = new Map();

if (yearNode) {
  yearNode.textContent = new Date().getFullYear();
}

function stopModalMedia(modal) {
  modal.querySelectorAll("video").forEach((video) => {
    video.pause();
    video.currentTime = 0;
  });

  const slideshowId = modal.getAttribute("id");
  const slideshowTimer = modalSlideshows.get(slideshowId);

  if (slideshowTimer) {
    clearInterval(slideshowTimer);
    modalSlideshows.delete(slideshowId);
  }
}

function startSlideshow(modal) {
  const slides = modal.querySelectorAll(".slide");

  if (slides.length <= 1) {
    return;
  }

  let activeIndex = 0;
  slides.forEach((slide, index) => {
    slide.classList.toggle("is-active", index === 0);
  });

  const intervalId = setInterval(() => {
    slides[activeIndex].classList.remove("is-active");
    activeIndex = (activeIndex + 1) % slides.length;
    slides[activeIndex].classList.add("is-active");
  }, 2200);

  modalSlideshows.set(modal.getAttribute("id"), intervalId);
}

function prepareVideoFallback(modal) {
  const video = modal.querySelector("video");
  const fallback = modal.querySelector(".video-fallback");

  if (!video || !fallback) {
    return;
  }

  const showFallback = () => {
    video.hidden = true;
    fallback.hidden = false;
  };

  video.addEventListener("error", showFallback, { once: true });
  video.querySelectorAll("source").forEach((source) => {
    source.addEventListener("error", showFallback, { once: true });
  });
}

function startModalVideo(video) {
  if (!video || video.hidden) {
    return;
  }

  video.pause();
  video.currentTime = 0;
  video.load();

  const tryPlay = () => {
    video.play().catch(() => {});
  };

  if (video.readyState >= 2) {
    tryPlay();
    return;
  }

  video.addEventListener("loadeddata", tryPlay, { once: true });
}

document.querySelectorAll("dialog").forEach((modal) => {
  prepareVideoFallback(modal);
});

mediaButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const targetId = button.getAttribute("data-modal-target");
    const modal = document.getElementById(targetId);

    if (!modal || typeof modal.showModal !== "function") {
      return;
    }

    modal.showModal();

    const video = modal.querySelector("video");
    startModalVideo(video);

    if (modal.querySelector("[data-slideshow]")) {
      startSlideshow(modal);
    }
  });
});

closeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const modal = button.closest("dialog");

    if (modal) {
      stopModalMedia(modal);
      modal.close();
    }
  });
});

document.querySelectorAll("dialog").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    const bounds = modal.getBoundingClientRect();
    const clickedOutside =
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom;

    if (clickedOutside) {
      stopModalMedia(modal);
      modal.close();
    }
  });

  modal.addEventListener("close", () => {
    stopModalMedia(modal);
  });
});
