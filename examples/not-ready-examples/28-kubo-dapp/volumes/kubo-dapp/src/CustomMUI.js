import { styled } from '@mui/material/styles';

import Button from '@mui/material/Button';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';


export const VisuallyHiddenInput = styled('input')({
   clip: 'rect(0 0 0 0)',
   clipPath: 'inset(50%)',
   height: 1,
   overflow: 'hidden',
   position: 'absolute',
   bottom: 0,
   left: 0,
   whiteSpace: 'nowrap',
   width: 1,
 });

 export function FileUploadBtn({onChange, className, disabled}){
  return (
    <Button
      component="label"
      role={undefined}
      variant="outlined"
      tabIndex={-1}
      startIcon={<CloudUploadIcon />}
      className="btn-upload"
      disabled={disabled}
    >
      Upload File
      <VisuallyHiddenInput 
        type="file"
        accept="image/*"
        name="data"
        id="file-upload"
        onChange={onChange}
        className={className}
      />
    </Button>
  );
 };