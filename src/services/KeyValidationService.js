import { chatLimitService } from './database/ChatLimitService.js';
import { supabaseService } from './database/SupabaseService';
import { userService } from './User.service';

class KeyValidationService {
    constructor() {
        this.STORAGE_KEY = 'wormgpt_access_key';
        this.BASE_URL = import.meta.env.VITE_API_URL;
    }

    validateKeyFormat(key) {
        if (!key) return false;
        
        // Convert to uppercase for consistent validation
        key = key.toUpperCase();
        
        // Accept WR-TEST12345 and regular keys (WR-XXXXXXXXXX)
        return key === "WR-TEST12345" || /^WR-[A-Z0-9]{10}$/.test(key);
    }

    async validateKey(key) {
        try {
            if (!this.validateKeyFormat(key)) {
                return { 
                    valid: false, 
                    message: 'Invalid key format. Key should start with WR- followed by 10 characters' 
                };
            }

            const response = await fetch(`${this.BASE_URL}/validate-key`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ key: key.toUpperCase() })
            });

            const data = await response.json();
            
            if (data.valid) {
                // Check if this is a different key
                const currentKey = (await this.getKeyData())?.key;
                const isNewKey = !currentKey || currentKey !== key.toUpperCase();

                const keyData = {
                    key: key.toUpperCase(),
                    expiryTime: data.expiryTime,
                    activatedAt: new Date().toISOString()
                };

                // Save only to database
                await this.saveKeyToDatabase(keyData);

                // Reset chat limits if it's a new key
                if (isNewKey) {
                    await chatLimitService.resetChatLimit();
                }

                // Calculate remaining time
                const remaining = await this.getRemainingTime();
                return {
                    ...data,
                    message: `Key activated successfully. Expires in ${remaining.hours}h ${remaining.minutes}m`
                };
            }
            
            return data;
        } catch (error) {
            console.error('Key validation error:', error);
            return { 
                valid: false, 
                message: 'Error connecting to validation server. Please try again.' 
            };
        }
    }

    async saveKeyToDatabase(keyData) {
        const userId = userService.getCurrentUserId();
        try {
            // Ensure user exists first
            await supabaseService.ensureUser(userId);
            
            const { error } = await supabaseService.client
                .from('key_validation')
                .upsert({
                    user_id: userId,
                    key_value: keyData.key,
                    expiry_time: keyData.expiryTime,
                    activated_at: keyData.activatedAt,
                    updated_at: new Date().toISOString()
                }, {
                    onConflict: 'user_id'
                })
                .select()
                .single();

            if (error) throw error;
        } catch (error) {
            console.error('Failed to save key to database:', error);
        }
    }

    async getKeyFromDatabase() {
        const userId = userService.getCurrentUserId();
        try {
            const { data, error } = await supabaseService.client
                .from('key_validation')
                .select('key_value, expiry_time, activated_at')
                .match({ user_id: userId })
                .maybeSingle();

            if (error || !data) return null;
            
            return {
                key: data.key_value,
                expiryTime: data.expiry_time,
                activatedAt: data.activated_at
            };
        } catch (error) {
            console.error('Failed to get key from database:', error);
            return null;
        }
    }

    async isKeyValid() {
        try {
            const keyData = await this.getKeyFromDatabase();
            if (!keyData) return false;

            const now = new Date();
            const expiryTime = new Date(keyData.expiryTime);
            return now < expiryTime;
        } catch (error) {
            console.error('Error checking key validity:', error);
            return false;
        }
    }

    async getKeyData() {
        try {
            return await this.getKeyFromDatabase();
        } catch (error) {
            console.error('Failed to get key data:', error);
            return null;
        }
    }

    async getRemainingTime() {
        const keyData = await this.getKeyData();
        if (!keyData) {
            return {
                hours: 0,
                minutes: 0
            };
        }

        const now = new Date();
        const expiryTime = new Date(keyData.expiryTime);
        const diff = expiryTime - now;

        return {
            hours: Math.max(0, Math.floor(diff / (1000 * 60 * 60))),
            minutes: Math.max(0, Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)))
        };
    }
}

export const keyValidationService = new KeyValidationService();