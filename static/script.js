document.addEventListener("DOMContentLoaded", async () => {
    const form_login = document.getElementById("loginForm");

    if (form_login) {
      form_login.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
  
        const response = await fetch("/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ email, password })
        });
  
        const data = await response.json();
        document.getElementById("message").innerText = data.message;
  
        if (response.ok) {
          localStorage.setItem("token", data.token);
          window.location.href = "/personal-index";
        }
      });
    }

    const form_register = document.getElementById("registerForm");

    if (form_register) {
      form_register.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("name").value;
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
  
        const response = await fetch("/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ name, email, password })
        });
  
        const data = await response.json();
        document.getElementById("message").innerText = data.message;
  
        if (response.ok) {
          window.location.href = "/login-page";
        }
      });
    }

    const form_pr = document.getElementById("registerPR");

    if (form_pr) {
      form_pr.addEventListener("submit", async (e) => {
        e.preventDefault();
        const token = localStorage.getItem("token");
        const exo_id = parseInt(document.getElementById("exo_id").value);
        const pr = document.getElementById("pr").value;
        const quantity = parseInt(document.getElementById("quantity").value);
        const time = parseInt(document.getElementById("time").value);
        const date = document.getElementById("date").value;
        const added_weight = parseInt(document.getElementById("added_weight").value);
        const weight = parseInt(document.getElementById("weight").value);
        
        if (!token) {
        document.body.innerHTML = "<p>Veuillez vous connecter.</p>";
        return;
        }

        const response = await fetch("/personal-record", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ exo_id, pr, quantity, time, date, added_weight, weight })
        });
  
        const data = await response.json();
        document.getElementById("message").innerText = data.message;
  
        if (response.ok) {
          window.location.href = "/personal-record-add";
        }
      });
    }

    if (window.location.pathname === "/personal-index") {
      const token = localStorage.getItem("token");
    
      if (!token) {
        document.body.innerHTML = "<p>Veuillez vous connecter.</p>";
        return;
      }

      fetch("/pr-types", {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
        .then(res => res.json())
        .then(prTypes => {
          const select = document.getElementById("prSelect");
          prTypes.forEach(pr => {
            const option = document.createElement("option");
            option.value = `${pr.pr}:${pr.exercise}`;
            option.textContent = `${pr.exercise} - ${pr.pr}`;
            select.appendChild(option);
          });
        });

      fetch("/activities", {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
        .then(res => res.json())
        .then(activity => {
          const selectActivity = document.getElementById("prSelectActivity")
          activity.forEach(ac => {
            const optionActivity = document.createElement("option");
            option.value = ac;
            option.textContent = ac;
            selectActivity.appendChild(option);
          });
        });

      // Écoute l’événement de sélection
      document.getElementById("prSelect").addEventListener("change", (e) => {
        const selectedPr = e.target.value;
        if (selectedPr) {
          const [pr, exo] = selectedPr.split(":");
          window.location.href = `/personal-record/${encodeURIComponent(pr)}/${encodeURIComponent(exo)}`;
        }
      });
      document.getElementById("prSelectActivity").addEventListener("change", (f) => {
        const selectedAct = f.target.value;
        if (selectedAct) {
          window.location.href = `/strava/${selectedAct}`;
        }
      });
    }

    if (window.location.pathname.startsWith("/personal-record/") && window.location.pathname !== "/personal-record") {
      const body = document.querySelector('body');
      const prType = body.getAttribute('data-pr-type');
      const exoName = body.getAttribute('data-exo-name');
      const token = localStorage.getItem("token");
  
      if (!token) {
        document.body.innerHTML = "<p>Veuillez vous connecter.</p>";
        return;
      }
  
      try {
        const response = await fetch(`/get-personal-record/${prType}/${exoName}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
  
        const data = await response.json();
  
        if (!response.ok) {
          document.body.innerHTML = `<p>${data.message}</p>`;
          return;
        }
  
        const tbody = document.querySelector("#pr-table tbody");
        const added_weights = [];
        const dates = [];
  
        data.forEach(pr => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${pr.date}</td>
            <td>${pr.quantity}</td>
            <td>${pr.time}</td>
            <td>${pr.added_weight}</td>
            <td>${pr.weight}</td>
            <td>${pr.bodyweight}</td>
          `;
          tbody.appendChild(row);

          dates.push(pr.date);
          added_weights.push(pr.added_weight);
        });

        const ctx = document.getElementById("prChart").getContext("2d");
        new Chart(ctx, {
          type: "line",  // Type de graphique (line, bar, etc.)
          data: {
            labels: dates,  // Les dates pour l'axe X
            datasets: [{
              label: "Added weight",
              data: added_weights,  // Les données à afficher
              borderColor: "rgba(75, 192, 192, 1)",
              backgroundColor: "rgba(75, 192, 192, 0.2)",
              fill: true
            }]
          },
          options: {
            responsive: true,
            scales: {
              x: {
                title: {
                  display: true,
                  text: "Date"
                }
              },
              y: {
                title: {
                  display: true,
                  text: "Added weight"
                },
                beginAtZero: false
              }
            }
          }
        });
      } catch (error) {
        document.body.innerHTML = "<p>Erreur lors du chargement des PR.</p>";
      }
    }
  });
  