import React, { useState, useEffect } from "react";
import styles from "./Home.module.scss";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setSelectedClusterSet } from "../../app/store/config/actions";

const carouselImages = [
  "https://files.readme.io/af61828-network.png",
  "https://files.readme.io/af2cb93-kinfin.loglogpowerlaw.png",
  "https://www.researchgate.net/publication/345712334/figure/fig2/AS:981066009546754@1610915772838/Rarefaction-curve-of-proteomes-within-sets-defined-by-major-clades-within-the-2.ppm",
];

const Home = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [currentImage, setCurrentImage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImage((prev) => (prev + 1) % carouselImages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar
        position="sticky"
        color="inherit"
        sx={{
          zIndex: 1002,
          backgroundColor: "var(--bg-color)",
          boxShadow: "0px 2px 6px rgba(0,0,0,0.05)",
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            component="div"
            color="primary"
            onClick={() => navigate("/")}
            sx={{
              flexGrow: 1,
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            KinFin
          </Typography>

          <Button
            onClick={() => {
              navigate("/define-node-labels");
              dispatch(setSelectedClusterSet(null));
            }}
            color="primary"
            variant="contained"
            sx={{ borderRadius: "20px", padding: "6px 16px" }}
          >
            Start Analysis
          </Button>
        </Toolbar>
      </AppBar>

      <div className={styles.homeContainer}>
        <div className={styles.contentWrapper}>
          <div className={styles.leftSection}>
            <h1>KinFin Analysis</h1>
            <p>
              Interactive exploration of gene homology across taxa, bringing
              protein clustering insights to your browser.
            </p>
            <div className={styles.buttonGroup}>
              <Button
                variant="outlined"
                color="primary"
                onClick={() => setIsVideoOpen(true)}
                sx={{ borderRadius: "25px", padding: "10px 20px" }}
              >
                View Demo
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={() => navigate("/define-node-labels")}
                sx={{ borderRadius: "25px", padding: "10px 20px" }}
              >
                Start Analysis
              </Button>
            </div>
          </div>

          <div className={styles.rightSection}>
            <img
              src={carouselImages[currentImage]}
              alt={`KinFin slide ${currentImage + 1}`}
              className={styles.carouselImage}
            />
          </div>
        </div>

        <Dialog
          open={isVideoOpen}
          onClose={() => setIsVideoOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogContent sx={{ position: "relative", padding: 0 }}>
            <IconButton
              onClick={() => setIsVideoOpen(false)}
              sx={{
                position: "absolute",
                right: 8,
                top: 8,
                zIndex: 1,
                color: "#fff",
                backgroundColor: "rgba(0,0,0,0.5)",
                "&:hover": { backgroundColor: "rgba(0,0,0,0.7)" },
              }}
            >
              <CloseIcon />
            </IconButton>
            <iframe
              width="100%"
              height="500"
              src="https://www.youtube.com/embed/n-Jghkfi5fQ?si=-2VrDNf32AhtOvOW"
              title="KinFin Demo Video"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{ display: "block" }}
            ></iframe>
          </DialogContent>
        </Dialog>
      </div>
    </Box>
  );
};

export default Home;
