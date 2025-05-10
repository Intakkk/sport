document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("loginForm");

    if (form) {
      form.addEventListener("submit", async (e) => {
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
          window.location.href = "/personal-record-page";
        }
      });
    }

    if (window.location.pathname === "/personal-record-page") {
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
            option.value = pr;
            option.textContent = pr;
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
            const optionActivity = document.createElement("optionActivity");
            optionActivity.value = ac;
            optionActivity.textContent = ac;
            selectActivity.appendChild(optionActivity);
          });
        });

      // Écoute l’événement de sélection
      document.getElementById("prSelect").addEventListener("change", (e) => {
        const selectedPr = e.target.value;
        if (selectedPr) {
          window.location.href = `/personal-record-page/${selectedPr}`;
        }
      });
      document.getElementById("prSelectActivity").addEventListener("change", (f) => {
        const selectedAct = f.target.value;
        if (selectedAct) {
          window.location.href = `/strava/${selectedAct}`;
        }
      });
    }

    if (window.location.pathname.startsWith("/personal-record-page/") && window.location.pathname !== "/personal-record-page") {
      const prType = window.location.pathname.split("/").pop();
      const token = localStorage.getItem("token");
  
      if (!token) {
        document.body.innerHTML = "<p>Veuillez vous connecter.</p>";
        return;
      }
  
      try {
        const response = await fetch(`/personal-record/${prType}`, {
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
  