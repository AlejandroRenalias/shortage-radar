// Pages with no script of their own (the 404 page) only need the shared set-up.
start();
loadSource().then(renderChrome).catch(() => {});
