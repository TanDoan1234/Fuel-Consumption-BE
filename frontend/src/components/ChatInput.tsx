import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ChevronDown, ChevronUp, Sparkles, Send, History, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { toast } from 'sonner@2.0.3';
import { ThemeColor, Language } from '../App';
import { t } from '../utils/translations';

interface SavedInput {
  id: string;
  timestamp: string;
  label: string;
  data: {
    speedOverGround: string;
    windSpeed10M: string;
    waveHeight: string;
    wavePeriod: string;
    seaFloorDepth: string;
    temperature2M: string;
    oceanCurrentVelocity: string;
    shipType?: string;
  };
}

interface ChatInputProps {
  onSendMessage: (content: string, formData: any) => void | Promise<void>;
  themeColor: ThemeColor;
  isDarkMode: boolean;
  customColor: string;
  language: Language;
  isSending?: boolean;
}

const SHIP_TYPE_OPTIONS = [
  { value: 'Ceto', label: 'Ceto' },
  { value: 'Poseidon', label: 'Poseidon' },
  { value: 'Triton', label: 'Triton' },
];

export default function ChatInput({ onSendMessage, themeColor, isDarkMode, customColor, language, isSending = false }: ChatInputProps) {
  // 8 features theo benchmark FuelCast + loại tàu
  const [speedOverGround, setSpeedOverGround] = useState('');
  const [windSpeed10M, setWindSpeed10M] = useState('');
  const [waveHeight, setWaveHeight] = useState('');
  const [wavePeriod, setWavePeriod] = useState('');
  const [seaFloorDepth, setSeaFloorDepth] = useState('');
  const [temperature2M, setTemperature2M] = useState('');
  const [oceanCurrentVelocity, setOceanCurrentVelocity] = useState('');
  const [shipType, setShipType] = useState('');
  
  const [textMessage, setTextMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [savedInputs, setSavedInputs] = useState<SavedInput[]>([]);

  // Load saved inputs from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('fluxmare_saved_inputs');
    if (saved) {
      try {
        setSavedInputs(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load saved inputs', e);
      }
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (isSending) {
      return;
    }

    if (!showForm) return;

    // Validate numeric features first
    const numericFeatures = [
      speedOverGround, windSpeed10M, waveHeight, wavePeriod,
      seaFloorDepth, temperature2M, oceanCurrentVelocity
    ];

    const emptyFields = numericFeatures.filter(f => !f).length;
    
    if (emptyFields > 0) {
      toast.error('Vui lòng nhập đầy đủ 8 đặc trưng!', {
        description: `Còn ${emptyFields} trường chưa điền`
      });
      return;
    }
    if (!shipType) {
      toast.error('Vui lòng chọn loại tàu!');
      return;
    }

    // Validate ranges based on provided min/max/mean
    const speed = parseFloat(speedOverGround);
    const windSpeed = parseFloat(windSpeed10M);
    const height = parseFloat(waveHeight);
    const period = parseFloat(wavePeriod);
    const depth = parseFloat(seaFloorDepth);
    const temp = parseFloat(temperature2M);
    const currentVel = parseFloat(oceanCurrentVelocity);

    if (speed < 0 || speed > 30) {
      toast.error('Ship_SpeedOverGround phải trong khoảng 0-30 m/s');
      return;
    }
    if (windSpeed < 0 || windSpeed > 50) {
      toast.error('Weather_WindSpeed10M phải trong khoảng 0-50 m/s');
      return;
    }
    if (height < 0.01 || height > 20) {
      toast.error('Weather_WaveHeight phải trong khoảng 0.01-20 m');
      return;
    }
    if (period < 0 || period > 30) {
      toast.error('Weather_WavePeriod phải trong khoảng 0-30 s');
      return;
    }
    if (depth < 0 || depth > 11000) {
      toast.error('Environment_SeaFloorDepth phải trong khoảng 0-11000 m');
      return;
    }
    if (temp < -20 || temp > 50) {
      toast.error('Weather_Temperature2M phải trong khoảng -20 đến 50°C');
      return;
    }
    if (currentVel < 0 || currentVel > 5) {
      toast.error('Weather_OceanCurrentVelocity phải trong khoảng 0-5 m/s');
      return;
    }

    const formData = {
      speedOverGround: speed,
      windSpeed10M: windSpeed,
      waveHeight: height,
      wavePeriod: period,
      seaFloorDepth: depth,
      temperature2M: temp,
      oceanCurrentVelocity: currentVel,
      shipType
    };

    // Save to history
    const savedInput: SavedInput = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      label: `Speed ${speed.toFixed(1)} | Wave ${height.toFixed(2)}m | Wind ${windSpeed.toFixed(1)}m/s | Ship ${shipType}`,
      data: {
        speedOverGround,
        windSpeed10M,
        waveHeight,
        wavePeriod,
        seaFloorDepth,
        temperature2M,
        oceanCurrentVelocity,
        shipType
      }
    };

    const newSavedInputs = [savedInput, ...savedInputs].slice(0, 10); // Keep last 10
    setSavedInputs(newSavedInputs);
    localStorage.setItem('fluxmare_saved_inputs', JSON.stringify(newSavedInputs));

    const message = `📊 Dự đoán Total.MomentaryFuel với 8 features:\n• Ship_SpeedOverGround: ${speed} m/s | ShipType: ${shipType}\n• Weather_WindSpeed10M: ${windSpeed} m/s | WaveHeight: ${height} m | WavePeriod: ${period} s\n• Environment_SeaFloorDepth: ${depth} m | Temperature2M: ${temp}°C | OceanCurrentVelocity: ${currentVel} m/s`;
    
    onSendMessage(message, formData);
    
    toast.success('Đã lưu vào lịch sử!', {
      description: 'Bạn có thể load lại từ dropdown History'
    });

    // Reset form
    setSpeedOverGround('');
    setWindSpeed10M('');
    setWaveHeight('');
    setWavePeriod('');
    setSeaFloorDepth('');
    setTemperature2M('');
    setOceanCurrentVelocity('');
    setShipType('');
  };

  const loadSavedInput = (inputId: string) => {
    const saved = savedInputs.find(s => s.id === inputId);
    if (saved) {
      setSpeedOverGround(saved.data.speedOverGround);
      setWindSpeed10M(saved.data.windSpeed10M);
      setWaveHeight(saved.data.waveHeight);
      setWavePeriod(saved.data.wavePeriod);
      setSeaFloorDepth(saved.data.seaFloorDepth);
      setTemperature2M(saved.data.temperature2M);
      setOceanCurrentVelocity(saved.data.oceanCurrentVelocity);
      setShipType(saved.data.shipType || '');
      
      toast.success('Đã load dữ liệu!', {
        description: saved.label
      });
    }
  };

  const clearHistory = () => {
    setSavedInputs([]);
    localStorage.removeItem('fluxmare_saved_inputs');
    toast.success('Đã xóa lịch sử!');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (textMessage.trim() && !isSending) {
        onSendMessage(textMessage.trim(), {});
        setTextMessage('');
      }
    }
  };

  // Theme colors
  const getColors = (theme: ThemeColor, dark: boolean) => {
    const base = {
      default: dark
        ? { bg: 'bg-[#0a0a0a]', inputBg: 'bg-[#1a1a1a]', border: 'border-[#e3d5f7]/40', text: 'text-[#e5e5e5]', inputText: 'text-white', accent: 'text-[#e3d5f7]', primary: 'bg-[#7c3aed]', primaryHover: 'hover:bg-[#6d28d9]' }
        : { bg: 'bg-white', inputBg: 'bg-[#fafafa]', border: 'border-[#2002a6]/50', text: 'text-[#1a1a1a]', inputText: 'text-gray-900', accent: 'text-[#2002a6]', primary: 'bg-[#2002a6]', primaryHover: 'hover:bg-[#1a0285]' },
      pink: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-pink-400/40', text: 'text-pink-50', inputText: 'text-white', accent: 'text-pink-300', primary: 'bg-pink-500', primaryHover: 'hover:bg-pink-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-pink-400/50', text: 'text-pink-950', inputText: 'text-gray-900', accent: 'text-pink-700', primary: 'bg-pink-600', primaryHover: 'hover:bg-pink-700' },
      blue: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-blue-400/50', text: 'text-blue-50', inputText: 'text-white', accent: 'text-blue-300', primary: 'bg-blue-500', primaryHover: 'hover:bg-blue-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-blue-400/50', text: 'text-blue-950', inputText: 'text-gray-900', accent: 'text-blue-700', primary: 'bg-blue-600', primaryHover: 'hover:bg-blue-700' },
      purple: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-purple-400/50', text: 'text-purple-50', inputText: 'text-white', accent: 'text-purple-300', primary: 'bg-purple-500', primaryHover: 'hover:bg-purple-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-purple-400/50', text: 'text-purple-950', inputText: 'text-gray-900', accent: 'text-purple-700', primary: 'bg-purple-600', primaryHover: 'hover:bg-purple-700' },
      ocean: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-cyan-400/50', text: 'text-cyan-50', inputText: 'text-white', accent: 'text-cyan-300', primary: 'bg-cyan-500', primaryHover: 'hover:bg-cyan-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-cyan-400/50', text: 'text-cyan-950', inputText: 'text-gray-900', accent: 'text-cyan-700', primary: 'bg-cyan-600', primaryHover: 'hover:bg-cyan-700' },
      sunset: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-orange-400/50', text: 'text-orange-50', inputText: 'text-white', accent: 'text-orange-300', primary: 'bg-orange-500', primaryHover: 'hover:bg-orange-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-orange-400/50', text: 'text-orange-950', inputText: 'text-gray-900', accent: 'text-orange-700', primary: 'bg-orange-600', primaryHover: 'hover:bg-orange-700' },
      emerald: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-emerald-400/50', text: 'text-emerald-50', inputText: 'text-white', accent: 'text-emerald-300', primary: 'bg-emerald-500', primaryHover: 'hover:bg-emerald-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-emerald-400/50', text: 'text-emerald-950', inputText: 'text-gray-900', accent: 'text-emerald-700', primary: 'bg-emerald-600', primaryHover: 'hover:bg-emerald-700' },
      rose: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-rose-400/50', text: 'text-rose-50', inputText: 'text-white', accent: 'text-rose-300', primary: 'bg-rose-500', primaryHover: 'hover:bg-rose-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-rose-400/50', text: 'text-rose-950', inputText: 'text-gray-900', accent: 'text-rose-700', primary: 'bg-rose-600', primaryHover: 'hover:bg-rose-700' },
      fuchsia: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-fuchsia-400/50', text: 'text-fuchsia-50', inputText: 'text-white', accent: 'text-fuchsia-300', primary: 'bg-fuchsia-500', primaryHover: 'hover:bg-fuchsia-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-fuchsia-400/50', text: 'text-fuchsia-950', inputText: 'text-gray-900', accent: 'text-fuchsia-700', primary: 'bg-fuchsia-600', primaryHover: 'hover:bg-fuchsia-700' },
      indigo: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-indigo-400/50', text: 'text-indigo-50', inputText: 'text-white', accent: 'text-indigo-300', primary: 'bg-indigo-500', primaryHover: 'hover:bg-indigo-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-indigo-400/50', text: 'text-indigo-950', inputText: 'text-gray-900', accent: 'text-indigo-700', primary: 'bg-indigo-600', primaryHover: 'hover:bg-indigo-700' },
      sky: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-sky-400/50', text: 'text-sky-50', inputText: 'text-white', accent: 'text-sky-300', primary: 'bg-sky-500', primaryHover: 'hover:bg-sky-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-sky-400/50', text: 'text-sky-950', inputText: 'text-gray-900', accent: 'text-sky-700', primary: 'bg-sky-600', primaryHover: 'hover:bg-sky-700' },
      teal: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-teal-400/50', text: 'text-teal-50', inputText: 'text-white', accent: 'text-teal-300', primary: 'bg-teal-500', primaryHover: 'hover:bg-teal-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-teal-400/50', text: 'text-teal-950', inputText: 'text-gray-900', accent: 'text-teal-700', primary: 'bg-teal-600', primaryHover: 'hover:bg-teal-700' },
      lime: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-lime-400/50', text: 'text-lime-50', inputText: 'text-white', accent: 'text-lime-300', primary: 'bg-lime-500', primaryHover: 'hover:bg-lime-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-lime-400/50', text: 'text-lime-950', inputText: 'text-gray-900', accent: 'text-lime-700', primary: 'bg-lime-600', primaryHover: 'hover:bg-lime-700' },
      amber: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-amber-400/50', text: 'text-amber-50', inputText: 'text-white', accent: 'text-amber-300', primary: 'bg-amber-500', primaryHover: 'hover:bg-amber-600' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-amber-400/50', text: 'text-amber-950', inputText: 'text-gray-900', accent: 'text-amber-700', primary: 'bg-amber-600', primaryHover: 'hover:bg-amber-700' },
      custom: dark
        ? { bg: 'bg-black', inputBg: 'bg-[#1a1a1a]', border: 'border-white/40', text: 'text-white', inputText: 'text-white', accent: 'text-white', primary: 'bg-white', primaryHover: 'hover:bg-gray-200' }
        : { bg: 'bg-white', inputBg: 'bg-white', border: 'border-gray-900/50', text: 'text-gray-900', inputText: 'text-gray-900', accent: 'text-gray-900', primary: 'bg-gray-900', primaryHover: 'hover:bg-gray-800' },
    };
    return base[theme];
  };

  const colors = getColors(themeColor, isDarkMode);

  return (
    <div 
      className={`border-t-2 ${colors.border} ${colors.bg} p-3 flex-shrink-0`}
      style={themeColor === 'custom' ? { borderColor: customColor + '60' } : {}}
    >
      <form onSubmit={handleSubmit} className="space-y-2 max-w-7xl mx-auto">
        {/* Chat Textarea */}
        <div className="relative">
          <Textarea
            placeholder="Hỏi về Total.MomentaryFuel hoặc nhập 8 features bên dưới... (Enter gửi, Shift+Enter xuống dòng)"
            value={textMessage}
            onChange={(e) => setTextMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            className={`w-full min-h-[60px] max-h-[100px] resize-none ${colors.inputBg} border-2 ${colors.border} text-sm pr-10 rounded-xl shadow-sm`}
            style={themeColor === 'custom' 
              ? { 
                  borderColor: customColor + '60',
                  color: isDarkMode ? "#ffffff" : "#0a0a0a",
                }
              : {
                  color: isDarkMode ? "#ffffff" : "#0a0a0a",
                }}
            rows={2}
          />
          <Sparkles className={`absolute top-3 right-3 h-4 w-4 ${colors.accent} opacity-50 pointer-events-none`} />
        </div>

        {/* Toggle Form Button + History */}
        <div className="flex items-center gap-2">
          <div className={`flex-1 h-px ${colors.border}`}></div>
          
          {/* History Dropdown */}
          {savedInputs.length > 0 && (
            <div className="flex items-center gap-1">
              <Select onValueChange={(value) => {
                if (value === 'clear') {
                  clearHistory();
                } else {
                  loadSavedInput(value);
                }
              }}>
                <SelectTrigger 
                  className={`${colors.inputBg} border ${colors.border} ${colors.text} h-6 px-2 text-xs w-auto`}
                  style={themeColor === 'custom' ? { borderColor: customColor + '60' } : {}}
                >
                  <History className="h-3 w-3 mr-1" />
                  <SelectValue placeholder={`Lịch sử (${savedInputs.length})`} />
                </SelectTrigger>
                <SelectContent>
                  {savedInputs.map((saved) => (
                    <SelectItem key={saved.id} value={saved.id} className="text-xs">
                      {new Date(saved.timestamp).toLocaleString('vi-VN', { 
                        day: '2-digit', 
                        month: '2-digit', 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })} - {saved.label}
                    </SelectItem>
                  ))}
                  <SelectItem value="clear" className="text-xs text-red-500">
                    🗑️ Xóa lịch sử
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <Button
            type="button"
            onClick={() => setShowForm(!showForm)}
            variant="ghost"
            size="sm"
            className={`${colors.accent} ${colors.primaryHover} text-xs h-6 px-2 flex items-center gap-1`}
          >
            {showForm ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {showForm ? 'Ẩn Form' : 'Form 8 Features'}
          </Button>
          <div className={`flex-1 h-px ${colors.border}`}></div>
        </div>

        {/* Form with 8 features */}
        <AnimatePresence>
          {showForm && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between mb-2">
                  <p 
                    className="text-xs font-medium"
                    style={themeColor === 'custom' 
                      ? { color: customColor } 
                      : {
                          color: isDarkMode ? colors.accent.replace('text-', '#') : colors.accent.replace('text-', '#'),
                        }}
                  >
                    ⚠️ Bắt buộc nhập đủ 8 đặc trưng để dự đoán Total.MomentaryFuel (kg/s)
                  </p>
                  {savedInputs.length > 0 && (
                    <p 
                      className="text-[10px]"
                      style={themeColor === 'custom' 
                        ? { color: customColor + 'CC' } 
                        : {
                            color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                          }}
                    >
                      💾 {savedInputs.length}/10 lịch sử
                    </p>
                  )}
                </div>

                {/* Row 1: Ship Speed, Wind Speed, Wave Height */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Tốc độ tàu' : 'Ship Speed'}* (m/s)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 4.92
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0 - 30"
                      value={speedOverGround}
                      onChange={(e) => setSpeedOverGround(e.target.value)}
                      min="0"
                      max="30"
                      step="0.01"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Tốc độ gió' : 'Wind Speed'}* (m/s)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 3.74
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0 - 50"
                      value={windSpeed10M}
                      onChange={(e) => setWindSpeed10M(e.target.value)}
                      min="0"
                      max="50"
                      step="0.01"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Độ cao sóng' : 'Wave Height'}* (m)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 0.72
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0.01 - 20"
                      value={waveHeight}
                      onChange={(e) => setWaveHeight(e.target.value)}
                      min="0.01"
                      max="20"
                      step="0.01"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                </div>

                {/* Row 2: Wave Period, Sea Floor Depth, Temperature */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Chu kỳ sóng' : 'Wave Period'}* (s)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 5.29
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0 - 30"
                      value={wavePeriod}
                      onChange={(e) => setWavePeriod(e.target.value)}
                      min="0"
                      max="30"
                      step="0.1"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Độ sâu đáy biển' : 'Sea Floor Depth'}* (m)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 127.46
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0 - 11000"
                      value={seaFloorDepth}
                      onChange={(e) => setSeaFloorDepth(e.target.value)}
                      min="0"
                      max="11000"
                      step="0.1"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Nhiệt độ' : 'Temperature'}* (°C)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 25.22
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="-20 - 50"
                      value={temperature2M}
                      onChange={(e) => setTemperature2M(e.target.value)}
                      min="-20"
                      max="50"
                      step="0.1"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                </div>

                {/* Row 3: Ocean Current Velocity & Ship Type */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Dòng chảy đại dương' : 'Ocean Current'}* (m/s)
                      <span 
                        className="text-[10px] ml-1"
                        style={{
                          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.65)",
                        }}
                      >
                        {language === 'vi' ? 'TB' : 'Mean'}: 0.26
                      </span>
                    </label>
                    <Input
                      type="number"
                      placeholder="0 - 5"
                      value={oceanCurrentVelocity}
                      onChange={(e) => setOceanCurrentVelocity(e.target.value)}
                      min="0"
                      max="5"
                      step="0.01"
                      className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs`}
                      style={themeColor === 'custom' 
                        ? { 
                            borderColor: customColor + '60',
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }
                        : {
                            color: isDarkMode ? "#ffffff" : "#0a0a0a",
                          }}
                    />
                  </div>
                  <div>
                    <label 
                      className="text-xs block mb-1.5 font-medium"
                      style={{
                        color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
                      }}
                    >
                      {language === 'vi' ? 'Loại tàu' : 'Ship Type'}*
                    </label>
                    <Select value={shipType} onValueChange={setShipType}>
                      <SelectTrigger
                        className={`${colors.inputBg} border-2 ${colors.border} h-9 text-xs font-medium ${
                          isDarkMode ? "text-white" : "text-gray-900"
                        }`}
                        style={themeColor === 'custom' 
                          ? { 
                              borderColor: customColor + '60',
                              color: isDarkMode ? "#ffffff" : "#0a0a0a",
                            } 
                          : {
                              color: isDarkMode ? "#ffffff" : "#0a0a0a",
                            }}
                      >
                        <SelectValue placeholder={language === 'vi' ? 'Chọn loại tàu' : 'Pick ship type'} />
                      </SelectTrigger>
                      <SelectContent
                        className={isDarkMode ? "bg-[#1a1a1a] border-gray-700" : "bg-white border-gray-300"}
                      >
                        {SHIP_TYPE_OPTIONS.map((option) => (
                          <SelectItem 
                            key={option.value} 
                            value={option.value} 
                            className={`text-xs font-medium ${
                              isDarkMode
                                ? "text-white hover:bg-gray-800 focus:bg-gray-800"
                                : "text-gray-900 hover:bg-gray-100 focus:bg-gray-100"
                            }`}
                          >
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div></div>
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  disabled={isSending}
                  className={`${colors.primary} ${colors.primaryHover} text-white w-full h-10 text-sm shadow-lg mt-2 ${isSending ? 'opacity-80 cursor-not-allowed' : ''}`}
                  style={themeColor === 'custom' ? { backgroundColor: customColor } : {}}
                >
                  {isSending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Dang xu ly...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Dự đoán Total.MomentaryFuel (kg/s)
                    </>
                  )}
                </Button>

                <div className="space-y-1 mt-1">
                  <p className={`text-[10px] ${colors.accent} opacity-60 text-center`}>
                    📋 Dữ liệu sẽ tự động lưu vào lịch sử (tối đa 10 lần)
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </form>
    </div>
  );
}
