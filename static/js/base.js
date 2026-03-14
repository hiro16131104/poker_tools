(() => {
  const menuBtn = document.getElementById("menu-btn");
  const mobileMenu = document.getElementById("mobile-menu");
  const iconOpen = document.getElementById("icon-open");
  const iconClose = document.getElementById("icon-close");
  menuBtn.addEventListener("click", () => {
    const open = mobileMenu.classList.toggle("hidden");
    menuBtn.setAttribute("aria-expanded", String(!open));
    iconOpen.classList.toggle("hidden", !open);
    iconClose.classList.toggle("hidden", open);
  });
})();
