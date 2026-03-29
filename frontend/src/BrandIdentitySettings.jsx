import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, Smartphone, Mail, Globe, MessageCircle, 
  User as UserIcon, Palette, Brain, ShieldCheck, Zap,
  CheckCircle2, ToggleLeft, Check, ImageIcon
} from 'lucide-react';

const defaultEmptyProfile = {
  id: null, name: '', system_instruction: '', archetype: 'sage', emoji_strategy: 2,
  dna_config_json: {}, logo_light_url: null, logo_dark_url: null,
  primary_color: '#394a25', secondary_color: '#5d4cbf', font_name: 'Inter',
  contact_json: { name: '', phone: '', email: '', website: '', whatsapp: '' },
  platform_toggles: { instagram: true, linkedin: true, facebook: true, x: true, tiktok: true, whatsapp: false }, 
  topics_include: [], topics_exclude: [], is_active: true
};

const archetypes = [
  { id: 'sage', label: 'The Sage', desc: 'Wise, analytical, authoritative.', icon: Brain },
  { id: 'creator', label: 'The Creator', desc: 'Imaginative, expressive.', icon: Palette },
  { id: 'maverick', label: 'The Maverick', desc: 'Bold, fast-paced.', icon: Zap },
  { id: 'mentor', label: 'The Mentor', desc: 'Warm, growth-focused.', icon: ShieldCheck },
  { id: 'curator', label: 'The Curator', desc: 'Tasteful, discerning.', icon: UserIcon }
];

const toneOptions = [
  "Professional", "Witty", "Empathetic", "Direct", "Inspirational", 
  "Educational", "Minimalist", "Aggressive", "Luxury", "Playful"
];

const emojiLabels = ["None", "Minimal", "Balanced", "Expressive", "Maximum"];
const platformKeys = ['instagram', 'linkedin', 'facebook', 'tiktok', 'whatsapp'];

export default function BrandIdentitySettings({ onSave }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [profileId, setProfileId] = useState(null);
  const [isActive, setIsActive] = useState(true);
  const [name, setName] = useState('');
  const [systemInstruction, setSystemInstruction] = useState('');
  const [archetype, setArchetype] = useState('sage');
  const [emojiStrategy, setEmojiStrategy] = useState(2);
  
  const [platformTones, setPlatformTones] = useState({ instagram: '', linkedin: '', facebook: '', tiktok: '', whatsapp: '' });
  const [activeTonePlatform, setActiveTonePlatform] = useState('instagram');
  const [topicsInclude, setTopicsInclude] = useState('');
  const [topicsExclude, setTopicsExclude] = useState('');
  
  const [platformToggles, setPlatformToggles] = useState(defaultEmptyProfile.platform_toggles);
  
  const [logoLight, setLogoLight] = useState(null);
  const [logoDark, setLogoDark] = useState(null);
  
  const [contact, setContact] = useState(defaultEmptyProfile.contact_json);
  
  const [primaryColor, setPrimaryColor] = useState('#394a25');
  const [secondaryColor, setSecondaryColor] = useState('#5d4cbf');
  const [fontName, setFontName] = useState('Inter');

  useEffect(() => {
    fetchActiveProfile();
  }, []);

  const fetchActiveProfile = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get('http://localhost:8000/api/brand-profiles/active', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.data?.status === 'success') {
        const p = res.data.active_profile ?? defaultEmptyProfile;
        setProfileId(p.id ?? null);
        setIsActive(p.is_active ?? true);
        setName(p.name || '');
        setSystemInstruction(p.system_instruction || '');
        setArchetype(p.archetype || 'sage');
        setEmojiStrategy(p.emoji_strategy ?? 2);
        
        const dna = p.dna_config_json || {};
        setPlatformTones(dna.platform_tones || { instagram: '', linkedin: '', facebook: '', tiktok: '', whatsapp: '' });
        
        setTopicsInclude(Array.isArray(p.topics_include) ? p.topics_include.join(', ') : '');
        setTopicsExclude(Array.isArray(p.topics_exclude) ? p.topics_exclude.join(', ') : '');
        setPlatformToggles(p.platform_toggles || defaultEmptyProfile.platform_toggles);
        
        setLogoLight(p.logo_light_url || null);
        setLogoDark(p.logo_dark_url || null);
        
        setContact(p.contact_json || defaultEmptyProfile.contact_json);
        
        setPrimaryColor(p.primary_color || '#394a25');
        setSecondaryColor(p.secondary_color || '#5d4cbf');
        setFontName(p.font_name || 'Inter');
      }
    } catch (err) {
      console.error("Failed to fetch profile", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        id: profileId,
        name,
        system_instruction: systemInstruction,
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        font_name: fontName,
        contact_json: contact,
        dna_config_json: { archetype, emoji_strategy: emojiStrategy, platform_tones: platformTones },
        platform_toggles: platformToggles,
        topics_include: topicsInclude.split(',').map(s => s.trim()).filter(Boolean),
        topics_exclude: topicsExclude.split(',').map(s => s.trim()).filter(Boolean),
        is_active: isActive,
        logo_light_url: logoLight,
        logo_dark_url: logoDark
      };
      await axios.post('http://localhost:8000/api/brand-profiles', payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (onSave) onSave();
      alert("Profile Saved Successfully.");
    } catch (err) {
      alert("Save failed: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToneChipClick = (tone) => {
    const currentTone = platformTones[activeTonePlatform] || '';
    if (currentTone.includes(tone)) {
      setPlatformTones({
        ...platformTones,
        [activeTonePlatform]: currentTone.replace(tone, '').replace(/,\s*,/, ',').trim().replace(/^,|,$/g, '')
      });
    } else {
      setPlatformTones({
        ...platformTones,
        [activeTonePlatform]: currentTone ? `${currentTone}, ${tone}` : tone
      });
    }
  };

  const handleLogoUpload = (e, type) => {
     const file = e.target.files[0];
     if (file) {
        const url = URL.createObjectURL(file);
        if (type === 'light') setLogoLight(url);
        if (type === 'dark') setLogoDark(url);
     }
  };

  const togglePlatform = (plat) => {
    setPlatformToggles({...platformToggles, [plat]: !platformToggles[plat]});
  };

  if (loading) return (
    <div className="min-h-screen bg-mesh flex items-center justify-center">
      <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-mesh pb-20 pt-8 px-4 md:px-10 lg:px-12 animate-fade-in font-sans">
      
      {/* HEADER SECTION (EXACT LAYOUT) */}
      <header className="flex justify-between items-start mb-10 max-w-[1600px] mx-auto border-b border-outline-variant/10 pb-6">
        <div>
          <h1 className="text-4xl font-black text-on-surface tracking-tight">Identity DNA</h1>
          <p className="text-muted text-sm font-semibold mt-1">
            Set your brand voice, visuals, and behavior. Every agent reads this before generating content.
          </p>
        </div>
        <button 
           onClick={() => setIsActive(!isActive)}
           className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-black uppercase tracking-widest transition-all ${isActive ? 'bg-primary text-white shadow-md' : 'bg-surface-variant text-muted border border-outline-variant/20'}`}
        >
           {isActive ? <CheckCircle2 size={16}/> : <ToggleLeft size={16}/>}
           {isActive ? 'AGENT ACTIVE' : 'AGENT PAUSED'}
        </button>
      </header>

      {/* 60/40 SPLIT STRUCTURE */}
      <div className="flex flex-col xl:flex-row gap-10 items-start max-w-[1600px] mx-auto">
        
        {/* LEFT PANE — FORM (60%) */}
        <div className="flex-1 w-full xl:w-[60%] space-y-10 order-2 xl:order-1">
          
          {/* Identity Core */}
          <section className="space-y-6">
             <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                <Brain size={18} className="text-primary" /> Identity Core
             </h2>
             
             <div>
                <label className="text-xs font-bold text-muted mb-2 block">Brand Name</label>
                <input 
                   type="text" value={name} onChange={e => setName(e.target.value)} 
                   placeholder="e.g. Agency Alpha"
                   className="w-full max-w-md bg-surface-container-high border border-outline-variant/20 rounded-lg p-3 focus:border-primary focus:ring-1 focus:ring-primary transition-all font-bold text-base text-on-surface placeholder:text-muted/50" 
                />
             </div>
             
             <div>
                <label className="text-xs font-bold text-muted mb-3 block">Soul Archetype</label>
                <div className="flex gap-4 overflow-x-auto pb-2 custom-scrollbar snap-x">
                   {archetypes.map(a => {
                      const isSelected = archetype === a.id;
                      const Icon = a.icon;
                      return (
                        <button 
                          key={a.id} onClick={() => setArchetype(a.id)}
                          className={`flex-shrink-0 w-[180px] p-4 rounded-xl flex flex-col items-start text-left shrink-0 transition-all snap-start ${isSelected ? 'bg-primary/5 border-2 border-primary text-on-surface shadow-sm' : 'bg-surface-container-high border-2 border-transparent text-muted hover:bg-surface-container-highest'}`}
                        >
                           <Icon size={20} className={`mb-3 ${isSelected ? 'text-primary' : 'opacity-60'}`} />
                           <span className={`font-black text-sm block mb-1 ${isSelected ? 'text-primary' : 'text-on-surface'}`}>{a.label}</span>
                           <span className="text-[10px] font-semibold leading-snug">{a.desc}</span>
                        </button>
                      );
                   })}
                </div>
             </div>

             <div>
                <label className="text-xs font-bold text-muted block">System Instruction</label>
                <span className="text-[10px] text-muted/70 block mb-2 font-medium">This controls every agent's behavior</span>
                <textarea 
                   value={systemInstruction} onChange={e => setSystemInstruction(e.target.value)} 
                   placeholder="You are a trusted expert in digital marketing..."
                   rows="6"
                   className={`w-full bg-surface-container-high border rounded-xl p-4 focus:border-primary focus:ring-1 transition-all text-sm leading-relaxed ${systemInstruction ? 'border-primary/30 text-on-surface font-medium' : 'border-outline-variant/20 text-muted/60'}`} 
                />
             </div>
          </section>

          {/* Nuance Engine */}
          <section className="space-y-6">
             <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                <MessageCircle size={18} className="text-primary" /> Nuance Engine
             </h2>

             <div>
                <label className="text-xs font-bold text-muted mb-3 block">Emoji Density</label>
                <input 
                   type="range" min="1" max="5" value={emojiStrategy} 
                   onChange={e => setEmojiStrategy(parseInt(e.target.value))} 
                   className="w-full h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-primary mb-2" 
                />
                <div className="flex justify-between px-1">
                   {emojiLabels.map((l, i) => (
                      <span key={l} className={`text-[9px] font-bold uppercase tracking-widest ${emojiStrategy === i + 1 ? 'text-primary' : 'text-muted/60'}`}>{l}</span>
                   ))}
                </div>
             </div>

             <div>
                <label className="text-xs font-bold text-muted mb-3 block">Platform Tone</label>
                <div className="flex gap-2 mb-4 overflow-x-auto pb-1 custom-scrollbar">
                   {platformKeys.map(plat => (
                     <button 
                        key={plat} onClick={() => setActiveTonePlatform(plat)}
                        className={`px-4 py-2 rounded-full text-xs font-black uppercase tracking-wider transition-all whitespace-nowrap ${activeTonePlatform === plat ? 'bg-primary text-white shadow-sm' : 'bg-surface-container-high text-muted hover:text-on-surface'}`}
                     >
                        {plat === 'tiktok' ? 'tt' : plat === 'whatsapp' ? 'wa' : plat.substring(0, 2)} {/* Render abbreviations */}
                        <span className="hidden sm:inline"> - {plat}</span>
                     </button>
                   ))}
                </div>
                
                <textarea 
                   value={platformTones[activeTonePlatform] || ''} onChange={e => setPlatformTones({...platformTones, [activeTonePlatform]: e.target.value})} 
                   placeholder={`Active tone instruction for ${activeTonePlatform}...`}
                   rows="4"
                   className={`w-full bg-surface-container-high border rounded-xl p-4 focus:border-primary transition-all text-sm ${platformTones[activeTonePlatform] ? 'border-primary/20 text-on-surface' : 'border-outline-variant/20 placeholder:text-muted/40'}`} 
                />
                
                <div className="mt-3">
                   <span className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 block">Quick Presets:</span>
                   <div className="flex flex-wrap gap-2">
                      {toneOptions.map(tone => {
                        const isSelected = platformTones[activeTonePlatform]?.includes(tone);
                        return (
                          <button 
                             key={tone} onClick={() => handleToneChipClick(tone)}
                             className={`px-3 py-1.5 rounded-md text-[11px] font-bold transition-all border ${isSelected ? 'bg-primary border-primary text-white shadow-sm' : 'bg-surface-container-high border-outline-variant/10 text-muted hover:border-primary/40 hover:text-primary'}`}
                          >
                             {tone}
                          </button>
                        );
                      })}
                   </div>
                </div>
             </div>
          </section>

          {/* Brand Visuals */}
          <section className="space-y-6">
             <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                <Palette className="text-primary" size={18} /> Brand Visuals
             </h2>

             {/* Swatch Inputs */}
             <div className="flex flex-col sm:flex-row gap-6">
                <div className="flex-1 space-y-2">
                   <label className="text-xs font-bold text-muted block">Primary color (used in backgrounds)</label>
                   <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full overflow-hidden border border-outline-variant/20 relative shadow-sm shrink-0">
                         <input type="color" value={primaryColor} onChange={e => setPrimaryColor(e.target.value)} className="w-[200%] h-[200%] absolute -top-5 -left-5 cursor-pointer opacity-0" />
                         <div className="w-full h-full" style={{backgroundColor: primaryColor}}></div>
                      </div>
                      <input type="text" value={primaryColor} onChange={e => setPrimaryColor(e.target.value)} className="bg-surface-container-high border border-outline-variant/10 rounded-lg px-3 py-1.5 font-mono text-xs w-24 focus:border-primary" />
                   </div>
                </div>
                <div className="flex-1 space-y-2">
                   <label className="text-xs font-bold text-muted block">Secondary color (used in accents)</label>
                   <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full overflow-hidden border border-outline-variant/20 relative shadow-sm shrink-0">
                         <input type="color" value={secondaryColor} onChange={e => setSecondaryColor(e.target.value)} className="w-[200%] h-[200%] absolute -top-5 -left-5 cursor-pointer opacity-0" />
                         <div className="w-full h-full" style={{backgroundColor: secondaryColor}}></div>
                      </div>
                      <input type="text" value={secondaryColor} onChange={e => setSecondaryColor(e.target.value)} className="bg-surface-container-high border border-outline-variant/10 rounded-lg px-3 py-1.5 font-mono text-xs w-24 focus:border-primary" />
                   </div>
                </div>
             </div>

             <div>
                <label className="text-xs font-bold text-muted mb-2 block">Font Family</label>
                <input type="text" value={fontName} onChange={e => setFontName(e.target.value)} placeholder="Inter" className="w-full max-w-[200px] bg-surface-container-high border border-outline-variant/10 rounded-lg px-3 py-2 font-sans font-bold text-sm focus:border-primary" />
             </div>

             {/* Logo Uploads */}
             <div>
                <label className="text-xs font-bold text-muted mb-2 block">Logo uploads:</label>
                <div className="flex flex-col sm:flex-row gap-4">
                   <div className="flex-1 h-[160px] relative group rounded-xl border-2 border-dashed border-outline-variant/20 bg-surface-container-high hover:border-primary/50 hover:bg-surface-container transition-all flex flex-col items-center justify-center text-center p-4">
                      <input type="file" accept="image/*" onChange={(e) => handleLogoUpload(e, 'light')} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" />
                      {logoLight ? (
                         <div className="w-full h-full p-2 relative z-10 flex items-center justify-center bg-white/5 rounded">
                            <img src={logoLight} className="max-h-full object-contain" alt="Light Logo" />
                            <div className="absolute top-1 right-1 bg-black/50 p-1 rounded-sm text-white opacity-0 group-hover:opacity-100"><Trash2 size={12}/></div>
                         </div>
                      ) : (
                         <div className="z-10 pointer-events-none space-y-2">
                            <Upload size={20} className="mx-auto text-muted" />
                            <p className="font-bold text-sm text-on-surface">+ Upload Light Logo</p>
                            <span className="text-[10px] text-muted font-medium block">for dark images</span>
                         </div>
                      )}
                   </div>
                   
                   <div className="flex-1 h-[160px] relative group rounded-xl border-2 border-dashed border-outline-variant/20 bg-surface-container-high hover:border-primary/50 hover:bg-surface-container transition-all flex flex-col items-center justify-center text-center p-4">
                      <input type="file" accept="image/*" onChange={(e) => handleLogoUpload(e, 'dark')} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" />
                      {logoDark ? (
                         <div className="w-full h-full p-2 relative z-10 flex items-center justify-center bg-white/90 rounded">
                            <img src={logoDark} className="max-h-full object-contain" alt="Dark Logo" />
                            <div className="absolute top-1 right-1 bg-black/50 p-1 rounded-sm text-white opacity-0 group-hover:opacity-100"><Trash2 size={12}/></div>
                         </div>
                      ) : (
                         <div className="z-10 pointer-events-none space-y-2">
                            <Upload size={20} className="mx-auto text-muted" />
                            <p className="font-bold text-sm text-on-surface">+ Upload Dark Logo</p>
                            <span className="text-[10px] text-muted font-medium block">for light images</span>
                         </div>
                      )}
                   </div>
                </div>
             </div>

             {/* Reference Images Drop */}
             <div>
                <label className="text-xs font-bold text-muted mb-2 block">Reference images (3-5):</label>
                <div className="h-[120px] w-full rounded-xl border-2 border-dashed border-outline-variant/20 bg-surface-container-high flex items-center justify-center relative hover:bg-surface-container transition-all">
                   <input type="file" multiple accept="image/*" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" />
                   <div className="flex items-center gap-3 text-muted z-10 pointer-events-none">
                      <ImageIcon size={20} />
                      <span className="text-xs font-bold">+ Drop files here</span>
                   </div>
                </div>
             </div>
          </section>

          {/* Contact Details */}
          <section className="space-y-4">
             <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                <Smartphone className="text-primary" size={18} /> Contact Details
             </h2>
             <span className="text-[10px] font-bold text-muted/70 uppercase tracking-widest block mb-1">
                (Injected into every image and caption automatically)
             </span>

             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col">
                   <label className="text-xs font-bold text-muted mb-1 ml-1">Name</label>
                   <input type="text" value={contact.name} onChange={e => setContact({...contact, name: e.target.value})} className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg px-4 py-3 font-medium text-sm focus:border-primary focus:ring-1" />
                </div>
                <div className="flex flex-col">
                   <label className="text-xs font-bold text-muted mb-1 ml-1">Phone</label>
                   <input type="text" value={contact.phone} onChange={e => setContact({...contact, phone: e.target.value})} className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg px-4 py-3 font-medium text-sm focus:border-primary focus:ring-1" />
                </div>
                <div className="flex flex-col">
                   <label className="text-xs font-bold text-muted mb-1 ml-1">Email</label>
                   <input type="email" value={contact.email} onChange={e => setContact({...contact, email: e.target.value})} className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg px-4 py-3 font-medium text-sm focus:border-primary focus:ring-1" />
                </div>
                <div className="flex flex-col">
                   <label className="text-xs font-bold text-muted mb-1 ml-1">Website</label>
                   <input type="text" value={contact.website} onChange={e => setContact({...contact, website: e.target.value})} className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg px-4 py-3 font-medium text-sm focus:border-primary focus:ring-1" />
                </div>
                <div className="flex flex-col md:col-span-2">
                   <label className="text-xs font-bold text-muted mb-1 ml-1">WhatsApp</label>
                   <input type="text" value={contact.whatsapp} onChange={e => setContact({...contact, whatsapp: e.target.value})} className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg px-4 py-3 font-medium text-sm focus:border-primary focus:ring-1" />
                </div>
             </div>
          </section>

          {/* Topic Watchlist & Toggles */}
          <section className="space-y-6">
             <div className="space-y-4">
                <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                   <Globe className="text-primary" size={18} /> Topic Watchlist
                </h2>
                <div className="space-y-3">
                   <div className="flex items-center gap-3">
                      <label className="text-xs font-bold text-muted w-16">Include:</label>
                      <input type="text" placeholder="AI tools, design..." value={topicsInclude} onChange={e => setTopicsInclude(e.target.value)} className="flex-1 bg-surface-container-low border border-outline-variant/20 rounded-lg px-3 py-2 text-sm focus:border-primary" />
                   </div>
                   <div className="flex items-center gap-3">
                      <label className="text-xs font-bold text-muted w-16">Exclude:</label>
                      <input type="text" placeholder="politics, controversy..." value={topicsExclude} onChange={e => setTopicsExclude(e.target.value)} className="flex-1 bg-surface-container-low border border-outline-variant/20 rounded-lg px-3 py-2 text-sm focus:border-primary" />
                   </div>
                </div>
             </div>

             <div className="space-y-4 pt-4">
                <h2 className="text-lg font-black tracking-tight text-on-surface flex items-center gap-2 border-b border-outline-variant/10 pb-2">
                   <Upload className="text-primary" size={18} /> Platform Toggles
                </h2>
                <div className="flex flex-wrap gap-4">
                   {platformKeys.map(plat => (
                      <div key={plat} className="flex items-center gap-2">
                         <span className="text-xs font-black uppercase w-6">{plat === 'tiktok' ? 'TT' : plat === 'whatsapp' ? 'WA' : plat.substring(0,2)}</span>
                         <button 
                            onClick={() => togglePlatform(plat)}
                            className={`w-10 h-6 rounded-full relative transition-colors ${platformToggles[plat] ? 'bg-primary' : 'bg-surface-variant'}`}
                         >
                            <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${platformToggles[plat] ? 'translate-x-5' : 'translate-x-1'}`}></div>
                         </button>
                      </div>
                   ))}
                </div>
             </div>
          </section>

          {/* SAVE BUTTON BOTTOM ONLY */}
          <div className="pt-10 border-t border-outline-variant/10">
            <button 
              onClick={handleSave} 
              disabled={saving}
              className="w-full bg-primary text-white py-4 rounded-xl font-black uppercase tracking-widest text-[11px] shadow-lg hover:shadow-primary/20 transition-all hover:-translate-y-0.5 disabled:opacity-50"
            >
              {saving ? 'SAVING...' : 'SAVE PROFILE'}
            </button>
          </div>

        </div>

        {/* RIGHT PANE — STICKY 380px PREVIEW (40%) */}
        <div className="hidden xl:block w-[380px] sticky top-10 order-1 xl:order-2 shrink-0">
          
          <h3 className="text-xs font-black tracking-widest uppercase text-muted mb-4 ml-2">Live Preview</h3>
          
          <div className="bg-surface-container/30 border border-outline-variant/10 rounded-[1.5rem] overflow-hidden shadow-2xl relative">
             
             {/* 16:9 Image Box */}
             <div className="aspect-[16/9] w-full relative bg-surface-container overflow-hidden">
                <img src="https://images.unsplash.com/photo-1542435503-956c224b17bc?w=400&q=80" className="w-full h-full object-cover opacity-80" alt="Generated preview" />
                <div className="absolute inset-0 opacity-40 mix-blend-color" style={{backgroundColor: primaryColor}}></div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
                
                {/* Logo Corner */}
                <div className="absolute top-4 right-4">
                   {logoLight ? (
                      <div className="h-6 max-w-[80px] px-2 py-1 bg-black/40 backdrop-blur-md rounded border border-white/10 flex items-center justify-center">
                         <img src={logoLight} className="h-full object-contain" alt="Logo" />
                      </div>
                   ) : (
                      <div className="px-2 py-1 bg-black/40 backdrop-blur-md rounded text-[7px] text-white uppercase font-black border border-white/10">
                         {name || 'YOUR LOGO'}
                      </div>
                   )}
                </div>

                {/* Subtitle center bottom - if wanted, text overlays */}
                <h4 className="absolute bottom-10 left-6 right-6 text-white text-lg font-black tracking-tighter drop-shadow-md text-balance leading-tight" style={{fontFamily: `${fontName}, sans-serif`}}>
                   Manifesting digital excellence securely.
                </h4>

                {/* Contact Strip exactly at bottom */}
                <div className="absolute bottom-0 left-0 right-0 h-6 bg-black/80 backdrop-blur-lg flex items-center justify-between px-3">
                   <span className="text-[7px] font-black uppercase text-white/90 truncate mr-2">
                     {contact.name ? `${contact.name} | ` : ''}
                     {contact.website || 'WEBSITE.COM'}
                   </span>
                   <span className="text-[7px] font-black uppercase text-white/90 whitespace-nowrap">
                     {contact.phone || contact.whatsapp || '+X XXX XXX XXXX'}
                   </span>
                </div>
             </div>
             
             <div className="p-5">
                {/* Sample Caption */}
                <span className="text-[8px] font-black uppercase tracking-widest text-muted block mb-2">Sample caption:</span>
                <p className="text-xs font-semibold leading-relaxed text-on-surface tracking-tight" style={{fontFamily: `${fontName}, sans-serif`}}>
                   {archetype === 'sage' && '"Knowledge compounds. By decoding the underlying metadata of our environment, we create certainty where others see chaos. 📊"'}
                   {archetype === 'maverick' && '"Your competitors are painting by numbers while the universe is a blank canvas. ⚡ We broke the algorithm."'}
                   {archetype === 'creator' && '"Imagine a digital soul that pulses with original frequency. We didn\'t just build an agent; we engineered a new aesthetic."'}
                   {archetype === 'mentor' && '"I understand the friction you\'re feeling, but resistance builds capacity. 🌱 Let\'s cultivate your digital footprint."'}
                   {archetype === 'curator' && '"True discernment is the art of strategic exclusion. We have filtered the noise to manifest only absolute geometric truths."'}
                </p>

                {/* Crop Previews */}
                <div className="mt-8 pt-5 border-t border-outline-variant/10">
                   <span className="text-[8px] font-black uppercase tracking-widest text-muted block mb-3">Platform crops:</span>
                   <div className="flex gap-4 items-end h-16">
                      {/* 1:1 IG */}
                      <div className="h-10 w-10 bg-surface-container relative rounded-sm border border-outline-variant/20 overflow-hidden flex items-center justify-center shrink-0">
                         <img src="https://images.unsplash.com/photo-1542435503-956c224b17bc?w=100&q=80" className="w-full h-full object-cover opacity-50 sepia-[0.3]" style={{mixBlendMode: 'luminosity'}} alt="1:1" />
                         <span className="absolute text-[8px] font-black text-on-surface">1:1</span>
                      </div>
                      {/* 1.91:1 LI/FB */}
                      <div className="h-6 w-12 bg-surface-container relative rounded-sm border border-outline-variant/20 overflow-hidden flex items-center justify-center shrink-0">
                         <img src="https://images.unsplash.com/photo-1542435503-956c224b17bc?w=100&q=80" className="w-full h-full object-cover opacity-50 sepia-[0.3]" style={{mixBlendMode: 'luminosity'}} alt="1.91:1" />
                         <span className="absolute text-[8px] font-black text-on-surface">1.91</span>
                      </div>
                      {/* 9:16 TT/Reels */}
                      <div className="h-14 w-8 bg-surface-container relative rounded-sm border border-outline-variant/20 overflow-hidden flex items-center justify-center shrink-0">
                         <img src="https://images.unsplash.com/photo-1542435503-956c224b17bc?w=100&q=80" className="w-full h-full object-cover opacity-50 sepia-[0.3]" style={{mixBlendMode: 'luminosity'}} alt="9:16" />
                         <span className="absolute text-[8px] font-black text-on-surface">9:16</span>
                      </div>
                   </div>
                </div>
             </div>

          </div>
        </div>
        
      </div>
    </div>
  );
}
