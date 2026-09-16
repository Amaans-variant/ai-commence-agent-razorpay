import { fetchPaymentStatus } from './api.js';
import { appendMessage } from './chat.js';

export function renderStage(response) {
    const stage = document.getElementById("visual-stage");
    if (!stage) return;

    if (response.action === "SHOW_PRODUCT" || response.action === "NEGOTIATE" || response.data) {
        document.body.classList.add("split-active");
        stage.innerHTML = "";
        
        if (response.data) {
            const card = document.createElement("div");
            card.className = "product-card card-enter";
            
            const priceInINR = response.data.display_price / 100;
            let priceHtml = `<div class="price">₹${priceInINR}</div>`;
            
            let checkoutHtml = "";
            if (response.payment_link) {
                const btnId = "btn-" + Math.random().toString(36).substring(7);
                checkoutHtml = `<a href="${response.payment_link}" target="_blank" id="${btnId}" class="pay-btn">Pay Now 🚀</a>`;
                pollPaymentStatus(response.payment_link, btnId);
            }

            card.innerHTML = `
                <h3>${response.data.name}</h3>
                <p class="desc">${response.data.description}</p>
                ${priceHtml}
                ${checkoutHtml}
            `;
            
            stage.appendChild(card);
            
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    card.classList.add("card-enter-active");
                });
            });
        }
    }
}

function pollPaymentStatus(link, btnId) {
    let pollInterval = setInterval(async () => {
        try {
            let statusData = await fetchPaymentStatus(link);
            
            if (statusData.status === "PAID") {
                let payBtn = document.getElementById(btnId);
                if (payBtn) {
                    payBtn.innerText = "Payment Confirmed ✅";
                    payBtn.style.background = "#059669"; 
                    payBtn.style.pointerEvents = "none"; 
                    payBtn.style.boxShadow = "none";
                }
                
                clearInterval(pollInterval);
                appendMessage("Thank you for your purchase! Your order has been confirmed.", "ai-msg");
            }
        } catch (e) {
            console.error("Polling error", e);
        }
    }, 3000); 
}
