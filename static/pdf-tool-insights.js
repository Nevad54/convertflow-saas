window.setupPdfToolInsights = function setupPdfToolInsights(config) {
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector(config.formSelector);
    if (!form) return;

    const fileInput = form.querySelector('input[name="file"]');
    const profileNode = document.getElementById(config.profileNodeId);
    const planNode = document.getElementById(config.planNodeId);
    if (!fileInput || !profileNode || !planNode) return;

    const touched = {};
    Object.entries(config.touchFields || {}).forEach(([key, selector]) => {
      const node = form.querySelector(selector);
      if (!node) return;
      touched[key] = false;
      const markTouched = () => { touched[key] = true; };
      node.addEventListener('change', markTouched);
      node.addEventListener('input', markTouched);
    });

    let requestId = 0;

    function setNodeMessage(node, message, isError) {
      node.innerHTML = message;
      node.style.color = isError ? '#b45309' : '';
      const card = node.closest('.insights-card');
      if (card) {
        card.dataset.state = isError ? 'error' : 'ready';
      }
    }

    async function refreshPlan() {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        setNodeMessage(planNode, planNode.dataset.empty || config.planEmptyText, false);
        return;
      }

      const current = ++requestId;
      setNodeMessage(planNode, config.planLoadingText, false);
      const planCard = planNode.closest('.insights-card');
      if (planCard) planCard.dataset.state = 'loading';
      const body = new FormData();
      body.append('file', file);
      if (typeof config.buildPlanBody === 'function') {
        config.buildPlanBody(form, body);
      }

      try {
        const response = await fetch(config.planEndpoint, { method: 'POST', body });
        if (!response.ok) {
          let detail = config.planErrorText;
          try {
            const payload = await response.json();
            detail = payload.detail || detail;
          } catch {}
          throw new Error(detail);
        }
        const plan = await response.json();
        if (current !== requestId) return;
        setNodeMessage(planNode, config.renderPlan(plan), false);
      } catch (error) {
        if (current !== requestId) return;
        setNodeMessage(planNode, error.message || config.planErrorText, true);
      }
    }

    async function refreshProfile() {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        setNodeMessage(profileNode, profileNode.dataset.empty || config.profileEmptyText, false);
        return;
      }

      const body = new FormData();
      body.append('file', file);
      setNodeMessage(profileNode, config.profileLoadingText, false);
      const profileCard = profileNode.closest('.insights-card');
      if (profileCard) profileCard.dataset.state = 'loading';

      try {
        const response = await fetch('/convert/pdf/profile', { method: 'POST', body });
        if (!response.ok) throw new Error(config.profileErrorText);
        const profile = await response.json();
        const applied = typeof config.applyProfileSuggestions === 'function'
          ? (config.applyProfileSuggestions(form, profile, touched) || [])
          : [];
        let html = config.renderProfile(profile);
        if (applied.length) {
          html += `<br><em>Suggested settings applied: ${applied.join(', ')}.</em>`;
        }
        setNodeMessage(profileNode, html, false);
        refreshPlan();
      } catch (error) {
        setNodeMessage(profileNode, error.message || config.profileErrorText, true);
      }
    }

    (config.planWatchSelectors || []).forEach(selector => {
      const node = form.querySelector(selector);
      if (!node) return;
      node.addEventListener('change', refreshPlan);
      node.addEventListener('input', refreshPlan);
    });

    fileInput.addEventListener('change', refreshProfile);
    fileInput.addEventListener('input', refreshProfile);
  });
};
