/* ============================================================
   js/main.js — 全站公共脚本
   规则要求：
   - 尽量依赖 jQuery，但不完全依赖（动画用 CSS 实现）
   - 代码放在 $(document).ready(function() { }); 里面
   - 不要注册 serviceWorker
   ============================================================ */

$(document).ready(function () {
  /* ---------- 模块化引入 header / footer ----------
     页面中留出占位符：
       <div id="header"></div>
       <div id="footer"></div>
     脚本会自动 fetch 对应的独立 HTML 文件并填充 */
  function loadComponent(id, url) {
    var $placeholder = $('#' + id);
    if ($placeholder.length === 0) {
      return;
    }
    fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Failed to load ' + url + ' (HTTP ' + response.status + ')');
        }
        return response.text();
      })
      .then(function (html) {
        $placeholder.html(html);
        // 组件加载完成后触发一个事件，方便后续逻辑
        $(document).trigger('component:loaded', [id, url]);
        // 如果加载的是 header，初始化 header 相关逻辑
        if (id === 'header') {
          initHeader();
        }
      })
      .catch(function (err) {
        // 静默失败：避免在无网络（file:// 协议）环境下刷错误
        console.warn('[main.js] ' + err.message);
      });
  }

  loadComponent('header', '/header.html');
  loadComponent('footer', '/footer.html');

  /* ---------- Header 交互：滚动固定 + 移动端菜单 ---------- */
  function initHeader() {
    var $header = $('.site-header');
    var $body = $('body');

    // 页面滚动时给 header 加阴影（固定定位在 CSS 里完成）
    function onScroll() {
      if ($(window).scrollTop() > 10) {
        $header.addClass('scrolled');
      } else {
        $header.removeClass('scrolled');
      }
    }

    // 给 body 加 padding-top，避免固定 header 遮挡内容
    if ($header.length && !$body.hasClass('has-fixed-header')) {
      $body.addClass('has-fixed-header');
    }

    onScroll();
    $(window).on('scroll', onScroll);

    // 移动端汉堡菜单
    $('#mobile-menu-toggle').on('click', function () {
      var $menu = $('#mobile-menu');
      var expanded = $menu.hasClass('open');
      $menu.toggleClass('open');
      $(this).attr('aria-expanded', String(!expanded));
    });

    // 点击菜单外区域关闭移动端菜单
    $(document).on('click', function (e) {
      if (!$(e.target).closest('#mobile-menu, #mobile-menu-toggle').length) {
        $('#mobile-menu').removeClass('open');
        $('#mobile-menu-toggle').attr('aria-expanded', 'false');
      }
    });
  }

  /* ---------- 页面加载完成后，若 header 已就绪也初始化 ---------- */
  if ($('.site-header').length) {
    initHeader();
  }

  /* ---------- 产品图片画廊切换 ---------- */
  initGallery();

  /* ---------- 产品图片画廊切换 ---------- */
  function initGallery() {
    var $main = $('#gallery-main');
    if (!$main.length) return;
    var $thumbs = $('#gallery-thumbs .gallery-thumb');
    if (!$thumbs.length) return;
    $thumbs.on('click', function () {
      var $t = $(this);
      var src = $t.data('gallery-img');
      if (!src) return;
      $main.attr('src', src);
      $thumbs.removeClass('border-[#0071e3] ring-2 ring-[#0071e3]/20').addClass('border-slate-200');
      $t.addClass('border-[#0071e3] ring-2 ring-[#0071e3]/20').removeClass('border-slate-200 hover:border-slate-300');
    });
  }

  /* ---------- 当前页高亮菜单 ---------- */
  function highlightCurrentNav() {
    var path = window.location.pathname;
    $('.site-header a[href]').each(function () {
      var href = $(this).attr('href');
      if (href && href !== '/' && path.indexOf(href) === 0) {
        $(this).addClass('text-[#0071e3] font-semibold');
      }
    });
    // 移动端底部导航高亮
    $('.mobile-nav-item').each(function () {
      var navPath = $(this).attr('data-nav');
      var isActive = (navPath === '/' && path === '/') ||
        (navPath !== '/' && path.indexOf(navPath) === 0);
      $(this).toggleClass('active', isActive);
    });
  }

  /* ---------- 滚动渐入动画 ----------
     页面元素添加 class="reveal"（可选 data-delay="100" 控制延迟），
     滚动进入视口时淡入上移。用原生 IntersectionObserver，
     不依赖 jQuery（规则：不能完全依赖 jQuery）。 */
  function initScrollReveal() {
    var revealEls = document.querySelectorAll('.reveal');
    if (revealEls.length === 0) return;
    if (!('IntersectionObserver' in window)) {
      revealEls.forEach(function (el) { el.classList.add('revealed'); });
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          el.classList.add('revealed');
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(function (el) { observer.observe(el); });
  }

  /* ---------- 频道墙横向滚动 ---------- */
  function initChannelRow() {
    var $row = $('.channel-row');
    if ($row.length === 0) return;
    // 鼠标滚轮横向滚动（桌面）
    $row.on('wheel', function (e) {
      if (Math.abs(e.originalEvent.deltaY) > Math.abs(e.originalEvent.deltaX)) {
        e.preventDefault();
        $row.scrollLeft($row.scrollLeft() + e.originalEvent.deltaY);
      }
    });
    // 左右箭头
    $('.channel-row-prev').on('click', function () {
      $row.animate({ scrollLeft: $row.scrollLeft() - $row.outerWidth() * 0.8 }, 400);
    });
    $('.channel-row-next').on('click', function () {
      $row.animate({ scrollLeft: $row.scrollLeft() + $row.outerWidth() * 0.8 }, 400);
    });
  }

  // 页面加载完成后初始化
  initScrollReveal();
  initChannelRow();
  $(document).on('component:loaded', function (e, id) {
    if (id === 'header') {
      highlightCurrentNav();
    }
  });

  /* ---------- 通用：滚动到锚点（平滑滚动由 CSS scroll-behavior 处理） ---------- */

  /* ---------- 表单：联系表单提交（占位，接入后端后替换） ---------- */
  $('form[data-ajax]').on('submit', function (e) {
    e.preventDefault();
    var $form = $(this);
    var $btn = $form.find('button[type="submit"]');
    var original = $btn.html();
    $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Sending...');

    // TODO: 后端地址待 website_info.md 确认后填入
    var endpoint = $form.attr('action') || '/api/contact';
    $.ajax({
      url: endpoint,
      method: 'POST',
      data: $form.serialize(),
      dataType: 'json',
      success: function () {
        $form.find('.form-status').remove();
        $form.append('<p class="form-status mt-4 text-sm text-green-600"><i class="fas fa-check-circle"></i> Thank you! Your message has been sent.</p>');
        $form.trigger('reset');
      },
      error: function () {
        $form.find('.form-status').remove();
        $form.append('<p class="form-status mt-4 text-sm text-red-600"><i class="fas fa-exclamation-circle"></i> Sorry, something went wrong. Please try again or contact us directly.</p>');
      },
      complete: function () {
        $btn.prop('disabled', false).html(original);
      },
    });
  });
});
