import { useState } from "react";
import slide1 from "../assets/onboarding/slide1.png";
import slide2 from "../assets/onboarding/slide2.png";
import slide3 from "../assets/onboarding/slide3.png";

const STORAGE_KEY = "pitwall_onboarding_complete";
const SLIDES = [slide1, slide2, slide3];

export default function OnboardingSlider({ onComplete }) {
  const [activeIndex, setActiveIndex] = useState(0);

  const isFirst = activeIndex === 0;
  const isLast = activeIndex === SLIDES.length - 1;

  function completeOnboarding() {
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // Continue into the dashboard if browser storage is unavailable.
    }
    onComplete?.();
  }

  function goPrevious() {
    setActiveIndex((index) => Math.max(0, index - 1));
  }

  function goNext() {
    if (isLast) {
      completeOnboarding();
      return;
    }
    setActiveIndex((index) => Math.min(SLIDES.length - 1, index + 1));
  }

  return (
    <section className="fixed inset-0 h-screen w-screen overflow-hidden bg-black">
      {SLIDES.map((image, index) => (
        <img
          key={image}
          src={image}
          alt=""
          aria-hidden={index !== activeIndex}
          className={[
            "absolute inset-0 h-screen w-screen object-cover transition-opacity duration-500 ease-out",
            index === activeIndex ? "opacity-100" : "opacity-0",
          ].join(" ")}
          style={{ width: "100vw", height: "100vh", objectFit: "cover" }}
        />
      ))}

      <button
        type="button"
        onClick={completeOnboarding}
        className="absolute right-3 top-3 z-10 rounded-md border border-white/40 bg-transparent px-3 py-2 text-[11px] font-black uppercase tracking-[0.18em] text-white shadow-[0_2px_14px_rgba(0,0,0,0.38)] transition-all duration-200 hover:border-white sm:right-6 sm:top-6 sm:px-4"
      >
        Skip
      </button>

      <div className="absolute bottom-14 left-3 z-10 flex max-w-[calc(100vw-1.5rem)] flex-wrap items-center gap-2 sm:bottom-6 sm:left-6 sm:max-w-none sm:gap-3">
        <button
          type="button"
          onClick={goPrevious}
          disabled={isFirst}
          className="rounded-md border border-white/40 bg-transparent px-3 py-2 text-[11px] font-black uppercase tracking-[0.16em] text-white shadow-[0_2px_14px_rgba(0,0,0,0.38)] transition-all duration-200 hover:border-white disabled:pointer-events-none disabled:opacity-40 sm:px-4"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={goNext}
          className="rounded-md border border-white/40 bg-transparent px-3 py-2 text-[11px] font-black uppercase tracking-[0.16em] text-white shadow-[0_2px_14px_rgba(0,0,0,0.38)] transition-all duration-200 hover:border-white sm:px-4"
        >
          {isLast ? "Get Started" : "Next"}
        </button>
      </div>

      <div className="absolute bottom-5 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 sm:bottom-7">
        {SLIDES.map((image, index) => (
          <button
            key={image}
            type="button"
            onClick={() => setActiveIndex(index)}
            aria-label={`Go to slide ${index + 1}`}
            aria-current={index === activeIndex}
            className={[
              "h-2 rounded-full border border-white/60 transition-all duration-300",
              index === activeIndex ? "w-8 border-white bg-transparent" : "w-2 bg-transparent hover:border-white",
            ].join(" ")}
          />
        ))}
      </div>
    </section>
  );
}
