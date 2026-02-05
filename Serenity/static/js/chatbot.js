document.addEventListener('DOMContentLoaded', function() {
    const chatbotToggler = document.querySelector(".chatbot-toggler");
    const closeBtn = document.querySelector(".close-btn");
    const chatbox = document.querySelector(".chatbox");
    const chatInput = document.querySelector(".chat-input textarea");
    const sendChatBtn = document.querySelector(".chat-input span");

    let userMessage = null;
    const inputInitHeight = chatInput.scrollHeight;

    // Function to add a message to the chatbox
    const createChatLi = (message, className) => {
        const chatLi = document.createElement("li");
        chatLi.classList.add("chat", `${className}`);
        
        // For outgoing messages, keep it simple
        if (className === "outgoing") {
            chatLi.innerHTML = `<p>${message}</p>`;
            return chatLi;
        }
        
        // For incoming messages, add formatting
        let chatContent = "";
        
        // If this is a thinking message or error message, keep it simple
        if (className.includes('pending') || className.includes('error')) {
            chatContent = `<span class="material-symbols-outlined">smart_toy</span><p>${message}</p>`;
            chatLi.innerHTML = chatContent;
            return chatLi;
        }
        
        // Format the message with better readability for seniors
        const formattedMessage = formatMessageForSeniors(message);
        chatContent = `<span class="material-symbols-outlined">smart_toy</span><div class="message-content">${formattedMessage}</div>`;
        chatLi.innerHTML = chatContent;
        return chatLi;
    };
    
    // Function to format messages for senior readability
    const formatMessageForSeniors = (message) => {
        if (!message) return '<p>Sorry, I couldn\'t process your request.</p>';
        
        // Store original message with asterisks for pattern matching
        const originalMessage = message;
        
        // Special formatting for Daily Health Check
        if (originalMessage.toLowerCase().includes('daily health check') || 
            originalMessage.toLowerCase().includes('health check today')) {
            return formatHealthCheckResponse(originalMessage);
        }
        
        // Special formatting for health advice about dizziness
        if (originalMessage.toLowerCase().includes('feeling dizzy') || 
            originalMessage.toLowerCase().includes('dizziness can') || 
            originalMessage.toLowerCase().includes('potential causes') ||
            originalMessage.toLowerCase().includes('what you can do right now') ||
            originalMessage.toLowerCase().includes('what to do right now') ||
            (originalMessage.toLowerCase().includes('dizzy') && originalMessage.toLowerCase().includes('causes'))) {
            return formatHealthAdviceResponse(originalMessage);
        }
        
        // Special formatting for nutrition advice
        if (originalMessage.toLowerCase().includes('healthy snack') || 
            originalMessage.toLowerCase().includes('good choice') || 
            originalMessage.toLowerCase().includes('greek yogurt') || 
            originalMessage.toLowerCase().includes('why it\'s a good choice')) {
            return formatNutritionAdvice(originalMessage);
        }
        
        // Process bullet points before removing asterisks
        let formattedMessage = message;
        
        // Handle bullet points with proper formatting
        formattedMessage = formattedMessage.replace(/\n\s*\* (.*?)(?=\n|$)/g, '<li>$1</li>');
        
        // Wrap bullet points in ul tags
        if (formattedMessage.includes('<li>')) {
            let parts = formattedMessage.split('<li>');
            let result = parts[0];
            let listContent = '';
            
            for (let i = 1; i < parts.length; i++) {
                if (parts[i].includes('</li>')) {
                    listContent += '<li>' + parts[i];
                }
            }
            
            if (listContent) {
                // Replace multiple consecutive lists with a single list
                listContent = listContent.replace(/<\/li>\s*<li>/g, '</li><li>');
                result += '<ul>' + listContent + '</ul>';
                formattedMessage = result;
            }
        }
        
        // Now remove asterisks for general formatting
        formattedMessage = formattedMessage.replace(/\*/g, '');
        
        // Handle headings (looking for words followed by colon)
        formattedMessage = formattedMessage.replace(/([A-Za-z\s]+):/g, '<h2>$1:</h2>');
        
        // Format disclaimers and important notes
        if (formattedMessage.toLowerCase().includes('disclaimer:')) {
            const parts = formattedMessage.split(/(disclaimer:.*)/i);
            if (parts.length > 1) {
                const beforeDisclaimer = parts[0];
                const disclaimer = '<div class="disclaimer">' + parts[1] + '</div>';
                formattedMessage = beforeDisclaimer + disclaimer;
            }
        }
        
        // Handle important considerations or tips
        if (formattedMessage.toLowerCase().includes('important reminder') || 
            formattedMessage.toLowerCase().includes('important considerations')) {
            formattedMessage = formattedMessage.replace(/(important\s+(?:reminder|considerations).*?)(\n\n|$)/is, 
                '<div class="health-tip">$1</div>$2');
        }
        
        // Make sure paragraphs are wrapped in p tags
        const paragraphs = formattedMessage.split('\n\n');
        formattedMessage = paragraphs.map(p => {
            // Skip if it's already wrapped in a tag
            if (p.trim().startsWith('<') && !p.trim().startsWith('<li>')) return p;
            return `<p>${p}</p>`;
        }).join('');
        
        // Clean up any remaining line breaks
        formattedMessage = formattedMessage.replace(/\n/g, '<br>');
        
        return formattedMessage;
    };

    // Special function to format health check responses
    const formatHealthCheckResponse = (message) => {
        let formattedResponse = '<div class="health-check-container">';
        
        // Add health check title
        formattedResponse += '<div class="health-check-title">Daily Health Check</div>';
        
        // Format introduction paragraph
        const introMatch = message.match(/^(.*?)(?=\*|\n\n)/s);
        if (introMatch) {
            formattedResponse += `<p>${introMatch[0].trim()}</p>`;
        }
        
        // Process the health check questions
        const questions = [];
        // Regular expression to match bullet points with their descriptions
        const regex = /\* (.*?)(?=\n\* |\n\n|$)/gs;
        let match;
        
        while ((match = regex.exec(message)) !== null) {
            const fullQuestion = match[1];
            
            // Extract the question title and description
            const titleMatch = fullQuestion.match(/^(?:\*\*)?(.*?)(?:\*\*)?:/);
            if (titleMatch) {
                const title = titleMatch[1].replace(/\*\*/g, '');
                const description = fullQuestion.substr(titleMatch[0].length).trim();
                
                questions.push({
                    title: title,
                    description: description
                });
            } else {
                // If no colon format, just use the whole question
                questions.push({
                    title: '',
                    description: fullQuestion.replace(/\*\*/g, '')
                });
            }
        }
        
        // Add formatted questions to the response
        for (const question of questions) {
            formattedResponse += '<div class="health-check-section">';
            if (question.title) {
                formattedResponse += `<div class="health-check-question">${question.title}</div>`;
            }
            formattedResponse += `<div class="health-check-description">${question.description}</div>`;
            formattedResponse += '</div>';
        }
        
        // Extract and format the important reminder/disclaimer
        const reminderMatch = message.match(/\*\*Important Reminder:\*\*(.*?)(?=\n\n|$)/s);
        if (reminderMatch) {
            const reminder = reminderMatch[1].trim().replace(/\*\*/g, '');
            formattedResponse += `<div class="health-check-reminder"><strong>Important Reminder</strong>${reminder}</div>`;
        }
        
        formattedResponse += '</div>';
        return formattedResponse;
    };

    // Function to format health advice responses
    const formatHealthAdviceResponse = (message) => {
        // Create a container for the health advice
        let formattedOutput = '<div class="health-advice">';
        
        // Extract sections using regex patterns first, before removing asterisks
        const titleMatch = message.match(/^(.*?)(?=\n|$)/);
        const title = titleMatch ? titleMatch[0] : 'Health Advice';
        
        // Add the title
        formattedOutput += `<h2>${title.replace(/\*/g, '')}</h2>`;
        
        // Process the message into structured sections
        const sections = [];
        let currentSection = null;
        let currentSubsection = null;
        const lines = message.split('\n');
        
        // Process sections and bullet points
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            
            // Check for main section headings (e.g., "Potential Causes:")
            const sectionMatch = line.match(/^([A-Za-z\s]+):(.*)$/);
            if (sectionMatch) {
                if (currentSection) {
                    sections.push(currentSection);
                }
                
                currentSection = {
                    title: sectionMatch[1].trim(),
                    content: [],
                    subsections: []
                };
                
                // If there's content after the colon, add it
                if (sectionMatch[2].trim()) {
                    currentSection.content.push(sectionMatch[2].trim());
                }
                
                currentSubsection = null;
                continue;
            }
            
            // Check for subsection headings (numbered items or capitalized phrases)
            const subsectionMatch = line.match(/^(\d+\.\s+|[A-Z][a-z]+\s+[A-Z][a-z]+:)/);
            if (subsectionMatch && currentSection) {
                currentSubsection = {
                    title: line,
                    items: []
                };
                currentSection.subsections.push(currentSubsection);
                continue;
            }
            
            // Check for bullet points
            if (line.startsWith('*') && currentSection) {
                const bulletText = line.replace(/^\*\s*/, '');
                
                if (currentSubsection) {
                    currentSubsection.items.push(bulletText);
                } else {
                    currentSection.content.push({
                        type: 'bullet',
                        text: bulletText
                    });
                }
                continue;
            }
            
            // Regular content line
            if (currentSection) {
                if (currentSubsection) {
                    currentSubsection.items.push(line);
                } else {
                    currentSection.content.push({
                        type: 'text',
                        text: line
                    });
                }
            }
        }
        
        // Add the last section
        if (currentSection) {
            sections.push(currentSection);
        }
        
        // Format each section
        for (const section of sections) {
            formattedOutput += `<div class="advice-section">`;
            formattedOutput += `<h3>${section.title.replace(/\*/g, '')}:</h3>`;
            
            // Format regular content
            if (section.content.length > 0) {
                let hasBullets = section.content.some(item => typeof item === 'object' && item.type === 'bullet');
                
                if (hasBullets) {
                    formattedOutput += `<ul>`;
                    for (const item of section.content) {
                        if (typeof item === 'object') {
                            if (item.type === 'bullet') {
                                formattedOutput += `<li>${item.text.replace(/\*/g, '')}</li>`;
                            } else {
                                formattedOutput += `<p>${item.text.replace(/\*/g, '')}</p>`;
                            }
                        } else {
                            formattedOutput += `<p>${item.replace(/\*/g, '')}</p>`;
                        }
                    }
                    formattedOutput += `</ul>`;
                } else {
                    for (const item of section.content) {
                        if (typeof item === 'object') {
                            formattedOutput += `<p>${item.text.replace(/\*/g, '')}</p>`;
                        } else {
                            formattedOutput += `<p>${item.replace(/\*/g, '')}</p>`;
                        }
                    }
                }
            }
            
            // Format subsections
            for (const subsection of section.subsections) {
                formattedOutput += `<div class="advice-subsection">`;
                formattedOutput += `<h4>${subsection.title.replace(/\*/g, '')}</h4>`;
                
                if (subsection.items.length > 0) {
                    formattedOutput += `<ul>`;
                    for (const item of subsection.items) {
                        formattedOutput += `<li>${item.replace(/\*/g, '')}</li>`;
                    }
                    formattedOutput += `</ul>`;
                }
                
                formattedOutput += `</div>`;
            }
            
            formattedOutput += `</div>`;
        }
        
        // Add important or disclaimer sections if present
        if (message.toLowerCase().includes('important:') || message.toLowerCase().includes('remember:')) {
            formattedOutput += `<div class="health-tip">`;
            const importantMatch = message.match(/(important:|remember:)(.*?)(?=\n\n|$)/is);
            if (importantMatch) {
                formattedOutput += importantMatch[0].replace(/\*/g, '');
            }
            formattedOutput += `</div>`;
        }
        
        // Add continue/iterate note for dizziness information
        if (message.toLowerCase().includes('dizzy') || message.toLowerCase().includes('dizziness')) {
            formattedOutput += `<div class="health-next-steps">`;
            formattedOutput += `<p><strong>Continue to iterate?</strong> Yes, continue monitoring symptoms and consult a healthcare professional if dizziness persists or worsens.</p>`;
            formattedOutput += `</div>`;
        }
        
        // Add disclaimer if present
        if (message.toLowerCase().includes('disclaimer:')) {
            formattedOutput += `<div class="disclaimer">`;
            const disclaimerMatch = message.match(/(disclaimer:)(.*?)(?=\n\n|$)/is);
            if (disclaimerMatch) {
                formattedOutput += disclaimerMatch[0].replace(/\*/g, '');
            }
            formattedOutput += `</div>`;
        }
        
        formattedOutput += '</div>';
        return formattedOutput;
    };

    // Special function to format nutrition advice
    const formatNutritionAdvice = (message) => {
        let formattedOutput = '<div class="nutrition-advice">';
        const lines = message.split('\n');
        let title = 'Nutrition Advice';

        if (lines.length > 0 && lines[0].trim()) {
            title = lines[0].trim().replace(/\*\*/g, '');
            lines.shift();
        }

        formattedOutput += `<h2>${title}</h2>`;

        let currentSection = null;
        let sections = [];

        for (let line of lines) {
            line = line.trim();
            if (!line) continue;

            const sectionMatch = line.match(/^([A-Za-z\s]+):(.*)$/);
            if (sectionMatch) {
                if (currentSection) sections.push(currentSection);
                currentSection = {
                    title: sectionMatch[1].trim(),
                    items: []
                };
                if (sectionMatch[2].trim()) currentSection.items.push(sectionMatch[2].trim());
            } else if (line.startsWith('*')) {
                if (currentSection) {
                    currentSection.items.push(line);
                } else {
                    currentSection = {
                        title: "Recommendations",
                        items: [line]
                    };
                }
            } else if (line && currentSection) {
                currentSection.items.push(line);
            } else if (line) {
                currentSection = {
                    title: "Important Information",
                    items: [line]
                };
            }
        }

        if (currentSection) sections.push(currentSection);

        for (const section of sections) {
            formattedOutput += `<div class="nutrition-section">`;
            formattedOutput += `<h3>${section.title.replace(/\*\*/g, '')}:</h3>`;
            formattedOutput += `<ul class="nutrition-list">`;
            for (const item of section.items) {
                const cleanItem = item.replace(/^\*\s*/, '').replace(/\*\*/g, '');
                formattedOutput += `<li>${cleanItem}</li>`;
            }
            formattedOutput += `</ul></div>`;
        }

        if (message.toLowerCase().includes('tip:') || message.toLowerCase().includes('note:')) {
            formattedOutput += `<div class="nutrition-tip">`;
            const tipMatch = message.match(/(tip:|note:)(.*?)(?=\n\n|$)/is);
            if (tipMatch) {
                formattedOutput += tipMatch[0].replace(/\*\*/g, '');
            }
            formattedOutput += `</div>`;
        }

        if (message.toLowerCase().includes('important reminder') || 
            message.toLowerCase().includes('disclaimer') || 
            message.toLowerCase().includes('always consult')) {
            formattedOutput += `<div class="nutrition-disclaimer">`;
            const reminderMatch = message.match(/(important reminder|disclaimer|always consult)(.*?)(?=\n\n|$)/is);
            if (reminderMatch) {
                formattedOutput += `<strong>${reminderMatch[1]}</strong>${reminderMatch[2].replace(/\*\*/g, '')}`;
            }
            formattedOutput += `</div>`;
        }

        formattedOutput += '</div>';
        return formattedOutput;
    };

    // Function to handle API errors
    const handleApiError = (thinkingMsg, errorMessage) => {
        thinkingMsg.innerHTML = `<span class="material-symbols-outlined">error</span><p>${errorMessage}</p>`;
        thinkingMsg.classList.remove('pending');
        thinkingMsg.classList.add('error');
        chatbox.scrollTo(0, chatbox.scrollHeight);
    };

    // Function to handle user message submission
    const handleChat = () => {
        userMessage = chatInput.value.trim();
        if(!userMessage) return;

        // Clear input 
        chatInput.value = "";
        chatInput.style.height = `${inputInitHeight}px`;

        // Show user's message in the chatbox
        chatbox.appendChild(createChatLi(userMessage, "outgoing"));
        chatbox.scrollTo(0, chatbox.scrollHeight);
        
        // Show thinking message
        const thinkingMsg = createChatLi("Thinking...", "incoming pending");
        chatbox.appendChild(thinkingMsg);
        chatbox.scrollTo(0, chatbox.scrollHeight);

        console.log("Sending message to API:", userMessage);

        // Send message to backend with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: userMessage
            }),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            console.log("API Response status:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API Response data:", data);
            
            // Remove the "Thinking..." message
            thinkingMsg.remove();
            
            if (data.is_emergency) {
                // Show emergency response with alert styling
                const emergencyMsg = createChatLi(data.response, "incoming emergency");
                chatbox.appendChild(emergencyMsg);
                
                // Add emergency alert animation
                document.body.classList.add("emergency-alert");
                setTimeout(() => {
                    document.body.classList.remove("emergency-alert");
                }, 5000);
            } else if (data.error) {
                // Error response
                const errorMsg = createChatLi(data.response, "incoming error");
                chatbox.appendChild(errorMsg);
            } else {
                // Normal response with improved formatting
                const botResponse = createChatLi(data.response, "incoming");
                chatbox.appendChild(botResponse);
            }
            
            chatbox.scrollTo(0, chatbox.scrollHeight);
        })
        .catch(error => {
            console.error('Error:', error);
            if (error.name === 'AbortError') {
                handleApiError(thinkingMsg, "Request timed out. Please try again.");
            } else {
                handleApiError(thinkingMsg, "Oops! Something went wrong. Please try again.");
            }
        });
    };

    // Handle chat input with Enter key
    chatInput.addEventListener("keydown", (e) => {
        // Submit on Enter without Shift
        if(e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleChat();
        }
        
        // Adjust textarea height based on content
        setTimeout(() => {
            chatInput.style.height = `${inputInitHeight}px`;
            chatInput.style.height = `${chatInput.scrollHeight}px`;
        }, 0);
    });

    sendChatBtn.addEventListener("click", handleChat);
    closeBtn.addEventListener("click", () => document.body.classList.remove("show-chatbot"));
    chatbotToggler.addEventListener("click", () => document.body.classList.toggle("show-chatbot"));
});