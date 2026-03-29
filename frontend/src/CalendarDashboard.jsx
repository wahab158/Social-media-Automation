import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import moment from 'moment';
import { 
  ChevronLeft, 
  ChevronRight, 
  Instagram, 
  Facebook, 
  Linkedin, 
  Twitter, 
  Clock, 
  MoreVertical,
  LayoutGrid,
  Check,
  Video,
  MessageCircle,
  Lock,
  Search
} from 'lucide-react';

const CalendarDashboard = ({ brandId }) => {
  const [currentDate, setCurrentDate] = useState(moment().startOf('week'));
  const [events, setEvents] = useState([]);
  const [draftPool, setDraftPool] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('week'); // 'week' or 'month'

  // Postoria Vertical Axis (6am - 11pm)
  const hours = Array.from({ length: 18 }, (_, k) => k + 6);

  const fetchEvents = useCallback(async () => {
    if (!brandId) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const start = currentDate.clone().startOf(view).toISOString();
      const end = currentDate.clone().endOf(view).toISOString();
      
      const res = await axios.get(`http://localhost:8000/api/calendar?brand_id=${brandId}&start=${start}&end=${end}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (res.data.status === 'success') {
        const testData = res.data.posts && res.data.posts.length > 0 ? res.data.posts : [
           { id: 101, topic: 'Mastering Agentic Workflows for Digital Marketing.', scheduled_time: moment().startOf('week').add(1, 'day').hour(9).toISOString(), platform: 'ig,li', category: 'Educational', status: 'approved', format: 'image' },
           { id: 102, topic: 'Announcement: Our new platform is live.', scheduled_time: moment().startOf('week').add(3, 'days').hour(14).toISOString(), platform: 'x,fb', category: 'News', status: 'generated', format: 'text' },
           { id: 103, topic: 'Case Study: 300% ROI in 30 Days', scheduled_time: moment().startOf('week').add(4, 'days').hour(10).toISOString(), platform: 'li', category: 'Business', status: 'scheduled', format: 'carousel' }
        ];
        setEvents(testData);
      }
    } catch (err) {
      console.error("Calendar fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [brandId, currentDate, view]);

  useEffect(() => {
    fetchEvents();
    // Simulated Draft Pool
    setDraftPool([
      { id: 'd1', topic: 'The rise of Agentic SEO: How AI is changing search.', format: 'carousel', platform: 'li,x', category: 'News', image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=200&auto=format&fit=crop' },
      { id: 'd2', topic: 'Midnight Forest is the aesthetic of 2026.', format: 'image', platform: 'ig', category: 'Business', image: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=200&auto=format&fit=crop' }
    ]);
  }, [fetchEvents]);

  const generateDays = () => {
    if (view === 'week') {
       const start = currentDate.clone().startOf('week');
       return Array.from({ length: 7 }, (_, i) => start.clone().add(i, 'days'));
    } else {
       const start = currentDate.clone().startOf('month').startOf('week');
       const end = currentDate.clone().endOf('month').endOf('week');
       const numDays = end.diff(start, 'days') + 1;
       return Array.from({ length: numDays }, (_, i) => start.clone().add(i, 'days'));
    }
  };

  const days = generateDays();

  const getEventsForDayAndHour = (day, hour) => {
    return events.filter(e => {
       const m = moment(e.scheduled_time);
       return m.isSame(day, 'day') && m.hour() === hour;
    });
  };

  const getEventsForDay = (day) => {
    return events.filter(e => moment(e.scheduled_time).isSame(day, 'day'));
  };

  const handlePrev = () => setCurrentDate(prev => prev.clone().subtract(1, view));
  const handleNext = () => setCurrentDate(prev => prev.clone().add(1, view));
  const handleToday = () => setCurrentDate(moment().startOf(view));

  const PlatformIconList = ({ platforms }) => {
    const plats = (platforms || '').split(',');
    return (
       <div className="flex gap-1">
         {plats.map((p, i) => {
           let Icon = LayoutGrid;
           if (p === 'ig') Icon = Instagram;
           if (p === 'li') Icon = Linkedin;
           if (p === 'fb') Icon = Facebook;
           if (p === 'x') Icon = Twitter;
           if (p === 'tk') Icon = Video;
           if (p === 'wa') Icon = MessageCircle;
           return <Icon key={i} size={14} className={`text-muted slot-${p}`} />;
         })}
       </div>
    );
  };

  // Status mapping
  const getStatusColor = (status) => {
    switch (status) {
       case 'generated': return 'border-surface-container/50 bg-transparent text-muted';
       case 'approved': return 'bg-primary-container text-on-primary-container border-primary-container';
       case 'scheduled': return 'bg-secondary-container text-on-secondary-container border-secondary-container';
       case 'posted': return 'bg-tertiary-container text-on-tertiary-container border-tertiary-container';
       case 'failed': return 'bg-error-container text-on-error-container border-error-container';
       case 'manual': return 'bg-warning-container text-yellow-900 border-warning-container';
       default: return 'border-outline-variant/20 bg-surface-container';
    }
  };

  const getStatusBorderStr = (status) => {
     switch (status) {
        case 'generated': return 'border-l-surface-container-highest';
        case 'approved': return 'border-l-primary';
        case 'scheduled': return 'border-l-secondary';
        case 'posted': return 'border-l-tertiary';
        case 'failed': return 'border-l-error';
        case 'manual': return 'border-l-warning';
        default: return 'border-l-outline';
     }
  };

  const getCardHeight = (format) => {
     if (format === 'video') return 'h-24';
     if (format === 'carousel') return 'h-20';
     return 'h-16'; // defaults to 64px
  };

  return (
    <div className="min-h-screen bg-mesh text-on-surface font-sans flex flex-col">
      
      {/* POSTORIA CONTROLS BAR */}
      <header className="h-[72px] shrink-0 border-b border-outline-variant/10 bg-surface-container-low/50 backdrop-blur-md px-6 flex items-center justify-between z-40 sticky top-0">
         
         {/* Left Side: Navigation */}
         <div className="flex items-center gap-4">
            <button onClick={handleToday} className="px-4 py-2 border border-outline-variant/20 rounded-lg text-xs font-bold hover:bg-surface-container transition-colors">Today</button>
            <div className="flex items-center">
               <button onClick={handlePrev} className="p-2 border border-outline-variant/20 rounded-l-lg hover:bg-surface-container transition-colors"><ChevronLeft size={16}/></button>
               <button onClick={handleNext} className="p-2 border border-outline-variant/20 rounded-r-lg border-l-0 hover:bg-surface-container transition-colors"><ChevronRight size={16}/></button>
            </div>
            <span className="text-lg font-black tracking-tighter w-[200px]">
               {currentDate.format(view === 'month' ? 'MMMM YYYY' : 'MMMM YYYY')}
            </span>
         </div>

         {/* Right Side: Toggles & Actions */}
         <div className="flex items-center gap-4">
            <div className="flex items-center bg-surface-container rounded-lg p-1 border border-outline-variant/10">
               <button 
                  onClick={() => setView('week')}
                  className={`px-4 py-1.5 rounded-md text-[10px] font-black uppercase tracking-widest transition-all ${view === 'week' ? 'bg-primary text-white shadow-sm' : 'text-muted hover:text-on-surface'}`}
               >
                  Week
               </button>
               <button 
                  onClick={() => setView('month')}
                  className={`px-4 py-1.5 rounded-md text-[10px] font-black uppercase tracking-widest transition-all ${view === 'month' ? 'bg-primary text-white shadow-sm' : 'text-muted hover:text-on-surface'}`}
               >
                  Month
               </button>
            </div>
            
            {view === 'week' && (
               <button className="bg-primary hover:bg-primary/90 text-white px-5 py-2 rounded-lg font-black uppercase tracking-widest text-[10px] flex items-center gap-2 transition-all">
                  <CheckCircle2 size={16} />
                  Approve Week
               </button>
            )}
         </div>

      </header>

      {/* MAIN LAYOUT */}
      <div className="flex-1 overflow-hidden flex">
         
         {/* LEFT CALENDAR AREA */}
         <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar bg-surface/50 pb-20">
            
            {view === 'week' ? (
               // WEEK VIEW: Vertical Time Axis
               <div className="min-w-[1000px]">
                  
                  {/* Weekday Headers */}
                  <div className="grid grid-cols-[60px_repeat(7,minmax(0,1fr))] border-b border-outline-variant/10 sticky top-0 z-30 bg-surface/90 backdrop-blur-xl">
                     <div className="border-r border-outline-variant/10"></div> {/* Top Left Empty */}
                     {days.map((day, i) => {
                        const isToday = moment().isSame(day, 'day');
                        return (
                           <div key={i} className={`py-4 text-center border-r border-outline-variant/10 ${isToday ? 'bg-primary/5' : ''}`}>
                              <span className={`block text-[10px] font-black uppercase tracking-widest mb-1 ${isToday ? 'text-primary' : 'text-muted'}`}>{day.format('ddd')}</span>
                              <span className={`text-2xl font-black ${isToday ? 'text-primary' : 'text-on-surface'}`}>{day.format('D')}</span>
                           </div>
                        );
                     })}
                  </div>

                  {/* Hour Rows */}
                  <div className="relative">
                     {hours.map(hour => (
                        <div key={hour} className="grid grid-cols-[60px_repeat(7,minmax(0,1fr))] group hover:bg-surface-container/10 transition-colors">
                           
                           {/* Time Column (60px) */}
                           <div className="h-16 border-r border-b border-outline-variant/10 flex items-start justify-center pt-2">
                              <span className="text-[10px] font-black tracking-widest text-muted/60 uppercase">
                                 {moment({ hour }).format('h a')}
                              </span>
                           </div>

                           {/* Day Slots */}
                           {days.map((day, i) => {
                              const posts = getEventsForDayAndHour(day, hour);
                              const isToday = moment().isSame(day, 'day');
                              
                              return (
                                 <div key={i} className={`h-16 border-r border-b border-outline-variant/10 relative p-1 pb-0 ${isToday ? 'bg-primary/5' : ''}`}>
                                    {posts.map(post => {
                                       const isLocked = moment(post.scheduled_time).diff(moment(), 'minutes') < 5 && moment(post.scheduled_time).diff(moment(), 'minutes') >= 0;
                                       return (
                                          <div 
                                             key={post.id} 
                                             className={`absolute top-1 left-1 right-1 ${getCardHeight(post.format)} bg-surface-container-high rounded-md border border-l-4 ${getStatusBorderStr(post.status)} shadow-sm hover:shadow-md transition-all cursor-pointer z-10 p-2 flex flex-col justify-between overflow-hidden group/card`}
                                          >
                                             {/* Top Row: Platforms & Status */}
                                             <div className="flex justify-between items-start">
                                                <PlatformIconList platforms={post.platform} />
                                                <div className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest ${getStatusColor(post.status)} flex items-center gap-1 border`}>
                                                   {isLocked && <Lock size={8}/>}
                                                   {post.status}
                                                </div>
                                             </div>
                                             
                                             {/* Middle: Topic */}
                                             <p className="text-xs font-bold leading-tight truncate text-on-surface">{post.topic}</p>
                                             
                                             {/* Bottom: Category & Time */}
                                             <div className="flex justify-between items-end opacity-60 group-hover/card:opacity-100 transition-opacity">
                                                <span className="text-[8px] font-black uppercase text-muted tracking-wide bg-surface-variant px-1 rounded">{post.category}</span>
                                                <span className="text-[9px] font-bold text-muted flex items-center gap-1"><Clock size={10}/> {moment(post.scheduled_time).format('h:mm')}</span>
                                             </div>
                                          </div>
                                       );
                                    })}
                                    
                                    {/* Hover Target for Drag Drop */}
                                    <div className="absolute inset-x-1 inset-y-1 rounded border-2 border-dashed border-primary/40 bg-primary/10 opacity-0 group-hover:opacity-100 z-0 pointer-events-none transition-opacity"></div>
                                 </div>
                              );
                           })}
                        </div>
                     ))}
                  </div>

               </div>
            ) : (
               // MONTH VIEW: 7x5 Clean Grid
               <div className="p-8 h-full flex flex-col">
                  {/* Month Headers */}
                  <div className="grid grid-cols-7 border-b border-outline-variant/20 pb-4 mb-4">
                     {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (
                        <div key={d} className="text-center text-[10px] font-black uppercase tracking-[0.2em] text-muted">{d}</div>
                     ))}
                  </div>
                  
                  {/* Grid */}
                  <div className="flex-1 grid grid-cols-7 gap-1 auto-rows-fr">
                     {days.map((day, i) => {
                        const posts = getEventsForDay(day);
                        const isToday = moment().isSame(day, 'day');
                        const isOutside = !day.isSame(currentDate, 'month');

                        return (
                           <div 
                              key={i} 
                              onClick={() => {
                                 setCurrentDate(day.clone().startOf('week'));
                                 setView('week');
                              }}
                              className={`p-3 border border-outline-variant/10 rounded-xl flex flex-col hover:border-primary/40 cursor-pointer transition-colors ${isToday ? 'bg-primary/5 ring-1 ring-primary' : 'bg-surface-container/30'} ${isOutside ? 'opacity-40 grayscale pointer-events-none' : ''}`}
                           >
                              <span className={`text-lg font-bold ${isToday ? 'text-primary' : 'text-on-surface'}`}>{day.format('D')}</span>
                              
                              <div className="mt-auto pt-2 grid grid-cols-2 gap-1 content-end">
                                 {posts.map(p => (
                                    <div key={p.id} className={`h-1.5 rounded-full ${getStatusBorderStr(p.status).replace('border-l-', 'bg-')}`}></div>
                                 ))}
                              </div>
                           </div>
                        );
                     })}
                  </div>
               </div>
            )}
            
         </div>

         {/* RIGHT PANE: DRAFT POOL (Only in Week View) */}
         {view === 'week' && (
            <div className="w-[280px] shrink-0 border-l border-outline-variant/10 bg-surface-container-low flex flex-col h-full z-40 relative shadow-2xl overflow-hidden">
               
               <div className="p-5 border-b border-outline-variant/10">
                  <h3 className="text-sm font-black tracking-widest uppercase text-on-surface mb-3 flex items-center justify-between">
                     Draft Pool
                     <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[10px]">{draftPool.length}</span>
                  </h3>
                  <div className="relative">
                     <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                     <input type="text" placeholder="Search..." className="w-full bg-surface-container border border-outline-variant/20 rounded-lg pl-8 pr-3 py-2 text-xs font-bold focus:border-primary focus:ring-1" />
                  </div>
               </div>

               <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                  {draftPool.map(draft => (
                     <div key={draft.id} className="bg-surface-container rounded-xl border border-outline-variant/20 overflow-hidden cursor-grab hover:border-primary/40 hover:shadow-lg transition-all group">
                        {/* Image Preview */}
                        {draft.image ? (
                           <div className="h-28 w-full bg-surface-variant relative overflow-hidden">
                              <img src={draft.image} alt={draft.topic} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                              <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-1.5 py-0.5 rounded text-[8px] font-black text-white uppercase tracking-widest border border-white/20">
                                 {draft.category}
                              </div>
                           </div>
                        ) : (
                           <div className="h-16 w-full bg-surface-container-high flex items-center justify-center relative border-b border-outline-variant/10">
                              <span className="text-muted/50 font-bold text-xs uppercase tracking-widest">Text Post</span>
                           </div>
                        )}
                        
                        <div className="p-3">
                           <div className="flex justify-between items-start mb-2">
                              <PlatformIconList platforms={draft.platform} />
                              <MoreVertical size={14} className="text-muted" />
                           </div>
                           <p className="text-xs font-bold leading-snug line-clamp-2 text-on-surface">{draft.topic}</p>
                        </div>
                     </div>
                  ))}
               </div>

            </div>
         )}
         
      </div>

    </div>
  );
};

export default CalendarDashboard;
