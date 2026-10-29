	(function () {
		try {
			var storedTheme = localStorage.getItem('lumia-theme');
			var theme =
				storedTheme ??
				(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
			var named = {
				dracula: { dark: true, color: '#282a36' },
				alucard: { dark: false, color: '#fffbeb' },
				nord: { dark: true, color: '#2e3440' },
				'solarized-light': { dark: false, color: '#fdf6e3' },
				'solarized-dark': { dark: true, color: '#002b36' }
			};
			var preset = named.hasOwnProperty(theme) ? named[theme] : null;
			if (preset) {
				document.documentElement.dataset.theme = theme;
				if (preset.dark) document.documentElement.classList.add('dark');
				var metas = document.querySelectorAll('meta[name="theme-color"]');
				for (var i = 0; i < metas.length; i++) {
					metas[i].setAttribute('content', preset.color);
					metas[i].removeAttribute('media');
				}
			} else if (theme === 'dark') {
				document.documentElement.classList.add('dark');
			}

			var accents = {
				violet: 265,
				indigo: 290,
				bleu: 220,
				cyan: 200,
				sarcelle: 175,
				vert: 145,
				ambre: 50,
				terracotta: 25,
				rose: 340
			};
			var hue = accents[localStorage.getItem('lumia-accent')] ?? accents.violet;
			var lightness = theme === 'dark' ? 0.72 : 0.5;
			var accentLightness = theme === 'dark' ? 0.3 : 0.94;
			var accentChroma = theme === 'dark' ? 0.05 : 0.03;
			var root = document.documentElement.style;
			if (!preset) {
				root.setProperty('--primary', 'oklch(' + lightness + ' 0.2 ' + hue + ')');
				root.setProperty('--ring', 'oklch(' + lightness + ' 0.2 ' + hue + ')');
				root.setProperty(
					'--accent',
					'oklch(' + accentLightness + ' ' + accentChroma + ' ' + hue + ')'
				);
			}

			var scales = { sm: 0.9, md: 1, lg: 1.15, xl: 1.3, xxl: 1.5 };
			var scale = scales[localStorage.getItem('lumia-font-scale')] ?? 1;
			document.documentElement.style.fontSize = 16 * scale + 'px';

			var pairs = ['editorial', 'magazine', 'humaniste', 'technique'];
			var pair = localStorage.getItem('lumia-font-pair');
			document.documentElement.dataset.fontPair =
				pairs.indexOf(pair) === -1 ? pairs[0] : pair;

			if (localStorage.getItem('lumia-reading-comfort') === 'on') {
				document.documentElement.dataset.readingComfort = 'on';
			}
		} catch (e) {}
	})();
