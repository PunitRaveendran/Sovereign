/* ============================================================
   SOVEREIGN — Animations (Bento Cute Redesign)
   animations.js — orchestration for aesthetic UI interactions
   ============================================================ */

const { animate, stagger } = window.Motion || {};

class UIMotion {
  /**
   * Animates the login role cards staggering in with bouncy spring physics.
   */
  static animateLoginEntrance() {
    if (!animate) return;

    animate(
      ".login-hero",
      { opacity: [0, 1], x: [-40, 0] },
      { duration: 0.8, type: "spring", stiffness: 200, damping: 20 }
    );

    animate(
      ".login-panel",
      { opacity: [0, 1], x: [40, 0] },
      { duration: 0.8, type: "spring", stiffness: 200, damping: 20 }
    );

    animate(
      ".glass-tab-item",
      { opacity: [0, 1], y: [60, 0], scale: [0.8, 1] },
      {
        delay: stagger(0.1, { startDelay: 0.3 }),
        duration: 0.8,
        type: "spring",
        stiffness: 250,
        damping: 18
      }
    );
  }

  /**
   * Orchestrates the dashboard panels sliding in (Bento style).
   */
  static animateDashboardEntrance() {
    if (!animate) return;

    // Topbar drops down
    animate(
      "#topbar",
      { y: ["-100%", "0%"] },
      { duration: 0.6, type: "spring", stiffness: 220, damping: 22 }
    );

    // Sidebar panels bounce in
    animate(
      "#sidebar .bento-panel",
      { x: [-60, 0], opacity: [0, 1], scale: [0.95, 1] },
      { delay: stagger(0.1, { startDelay: 0.15 }), duration: 0.6, type: "spring", stiffness: 220, damping: 22 }
    );

    // Right panels bounce in
    animate(
      "#right-panel .bento-panel",
      { x: [60, 0], opacity: [0, 1], scale: [0.95, 1] },
      { delay: stagger(0.1, { startDelay: 0.25 }), duration: 0.6, type: "spring", stiffness: 220, damping: 22 }
    );

    // Chat area scales up playfully
    animate(
      "#chat-area",
      { opacity: [0, 1], scale: [0.9, 1], y: [30, 0] },
      { delay: 0.4, duration: 0.7, type: "spring", stiffness: 180, damping: 20 }
    );
  }

  /**
   * Animates a newly added chat message bubble.
   */
  static animateChatMessage(element) {
    if (!animate || !element) return;
    animate(
      element,
      { opacity: [0, 1], y: [40, 0], scale: [0.85, 1] },
      { duration: 0.7, type: "spring", stiffness: 250, damping: 20 }
    );
  }

  /**
   * Animates a newly added tool call or deliverable card.
   */
  static animateCard(element) {
    if (!animate || !element) return;
    animate(
      element,
      { opacity: [0, 1], x: [-20, 0], scale: [0.9, 1] },
      { duration: 0.6, type: "spring", stiffness: 280, damping: 22 }
    );
  }

  /**
   * Bind aesthetic hover interactions to common elements.
   * Includes 3D tilt and magnetic effects for a premium feel.
   */
  static bindHoverEffects() {
    if (!animate) return;

    // 1. Magnetic elements (Buttons, topbar icons, chips)
    document.querySelectorAll(".magnetic").forEach((el) => {
      if (el.dataset.magneticBound) return;
      el.dataset.magneticBound = "true";

      const strength = 15; // px movement

      el.addEventListener("mousemove", (e) => {
        const rect = el.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const deltaX = (e.clientX - centerX) / (rect.width / 2);
        const deltaY = (e.clientY - centerY) / (rect.height / 2);
        
        animate(el, { 
          x: deltaX * strength, 
          y: deltaY * strength,
          scale: 1.05
        }, { duration: 0.1 });
      });

      el.addEventListener("mouseleave", () => {
        animate(el, { x: 0, y: 0, scale: 1 }, { duration: 0.5, type: "spring", stiffness: 300, damping: 20 });
      });
      
      el.addEventListener("mousedown", () => {
        animate(el, { scale: 0.95 }, { duration: 0.1 });
      });
      el.addEventListener("mouseup", () => {
        animate(el, { scale: 1.05 }, { duration: 0.2 });
      });
    });

    // 2. 3D Tilt effect for Role Cards & Login Card
    document.querySelectorAll(".hover-tilt").forEach((el) => {
      if (el.dataset.tiltBound) return;
      el.dataset.tiltBound = "true";

      el.addEventListener("mousemove", (e) => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left; 
        const y = e.clientY - rect.top;  
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = ((y - centerY) / centerY) * -6; // Soft tilt
        const rotateY = ((x - centerX) / centerX) * 6;
        
        el.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        
        // Add dynamic shine overlay if it doesn't exist
        let shine = el.querySelector('.tilt-shine');
        if (!shine) {
          shine = document.createElement('div');
          shine.className = 'tilt-shine';
          shine.style.position = 'absolute';
          shine.style.inset = '0';
          shine.style.borderRadius = 'inherit';
          shine.style.pointerEvents = 'none';
          shine.style.zIndex = '10';
          el.appendChild(shine);
        }
        
        const angle = Math.atan2(y - centerY, x - centerX) * 180 / Math.PI - 90;
        shine.style.background = `linear-gradient(${angle}deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 60%)`;
      });
      
      el.addEventListener("mouseleave", () => {
        el.style.transform = `perspective(1200px) rotateX(0deg) rotateY(0deg) scale(1)`;
        el.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
        const shine = el.querySelector('.tilt-shine');
        if (shine) {
          shine.style.background = 'transparent';
        }
      });
      
      el.addEventListener("mouseenter", () => {
        el.style.transition = 'none'; 
      });
    });
    
    // 3. Scroll Reveal for long content (like chat or lists)
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0) scale(1)';
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.scroll-reveal').forEach(el => {
      if (el.dataset.scrollBound) return;
      el.dataset.scrollBound = "true";
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px) scale(0.98)';
      el.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
      observer.observe(el);
    });
  }

  static initCustomCursor() {
    const cursor = document.getElementById('custom-cursor');
    if (!cursor) return;

    let mouseX = 0;
    let mouseY = 0;
    let cursorX = 0;
    let cursorY = 0;

    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    const loop = () => {
      cursorX += (mouseX - cursorX) * 0.15;
      cursorY += (mouseY - cursorY) * 0.15;
      
      cursor.style.transform = `translate3d(${cursorX - 12}px, ${cursorY - 12}px, 0)`;
      
      requestAnimationFrame(loop);
    };
    loop();

    document.querySelectorAll('button, a, .role-card').forEach(el => {
      el.addEventListener('mouseenter', () => {
        cursor.style.width = '36px';
        cursor.style.height = '36px';
        cursor.style.marginLeft = '-6px';
        cursor.style.marginTop = '-6px';
      });
      el.addEventListener('mouseleave', () => {
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.marginLeft = '0px';
        cursor.style.marginTop = '0px';
      });
    });
  }
}

window.UIMotion = UIMotion;

document.addEventListener('DOMContentLoaded', () => {
  UIMotion.initCustomCursor();
});
