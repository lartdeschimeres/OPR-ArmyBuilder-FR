import React, { useRef, useState } from 'react';
import { Upload, FileUp, Check, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const FactionImport = ({ onImportSuccess }) => {
  const fileInputRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileSelect = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/factions/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult({
        success: true,
        message: response.data.message,
        unitsCount: response.data.units_count,
      });

      toast.success(response.data.message);
      
      if (onImportSuccess) {
        onImportSuccess();
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Erreur lors de l\'import';
      setResult({
        success: false,
        message: errorMsg,
      });
      toast.error(errorMsg);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          data-testid="import-faction-btn"
          variant="secondary"
          size="sm"
          className="bg-purple-600 hover:bg-purple-700 text-white"
        >
          <FileUp className="w-4 h-4 mr-2" />
          Importer Faction
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#3a3c36] border-[#4b4d46] text-white">
        <DialogHeader>
          <DialogTitle className="font-headings text-xl uppercase">
            Importer une Faction
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Importez un fichier JSON contenant les données d'une faction OPR.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.txt"
            onChange={handleFileSelect}
            className="hidden"
          />

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#4b4d46] rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
          >
            <Upload className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">
              Cliquez pour sélectionner un fichier
            </p>
            <p className="text-xs text-gray-500">
              Formats acceptés: .json, .txt
            </p>
          </div>

          {uploading && (
            <div className="flex items-center gap-2 text-blue-400">
              <div className="animate-spin w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full" />
              <span>Import en cours...</span>
            </div>
          )}

          {result && (
            <div
              className={`flex items-start gap-3 p-4 rounded-lg ${
                result.success
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'
              }`}
            >
              {result.success ? (
                <Check className="w-5 h-5 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 mt-0.5" />
              )}
              <div>
                <p className="font-medium">{result.message}</p>
                {result.unitsCount && (
                  <p className="text-sm opacity-80">
                    {result.unitsCount} unités chargées
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="bg-[#2e2f2b] rounded-lg p-4">
            <h4 className="font-semibold text-sm mb-2">Format attendu:</h4>
            <pre className="text-xs text-gray-400 overflow-x-auto">
{`{
  "faction": "Nom de la Faction",
  "game": "Age of Fantasy",
  "version": "FR-3.5.2",
  "units": [...]
}`}
            </pre>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
